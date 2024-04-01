from flask_socketio import SocketIO
import io
from dotenv import load_dotenv
from datetime import datetime, timezone
import shutil

from flask_pymongo import PyMongo
import zipfile
from gpt_engineer.tools.custom_steps import clarified_gen, lite_gen, self_heal
from gpt_engineer.core.preprompts_holder import PrepromptsHolder
from gpt_engineer.core.default.steps import execute_entrypoint, gen_code, improve
from gpt_engineer.core.default.paths import PREPROMPTS_PATH, memory_path
from gpt_engineer.core.default.file_store import FileStore
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from flask import Flask, jsonify, render_template, redirect, session, send_file, url_for, request
import os
from pathlib import Path
import openai
import json
import sys
import typer
import logging
import requests
import ast

from io import StringIO
# Import necessary modules and classes from your CLI application
from gpt_engineer.applications.cli.cli_agent import CliAgent
from gpt_engineer.applications.cli.file_selector import FileSelector
from gpt_engineer.core.ai import AI
from gpt_engineer.applications.cli.collect import collect_and_send_human_review
from gpt_engineer.core.base_memory import BaseMemory
from gpt_engineer.core.files_dict import FilesDict
from gpt_engineer.core.default.steps import curr_fn, setup_sys_prompt
from langchain.schema import AIMessage, HumanMessage, SystemMessage
# Type hint for chat messages
from typing import List, Union
from gpt_engineer.core.default.paths import CODE_GEN_LOG_FILE, ENTRYPOINT_FILE
from gpt_engineer.core.chat_to_files import chat_to_files_dict

Message = Union[AIMessage, HumanMessage, SystemMessage]

app = Flask(__name__)
# socketio = SocketIO(app)

# creates a Flask web app
app.secret_key = 'Nim123??'  # Set a secret key for session management
connected_clients = set()  # Set to store connected client IDs

socketio = SocketIO(app, ping_timeout=300000)  # 5 minutes

# Configure MongoDB connection
app.config['MONGO_URI'] = 'mongodb+srv://naginamafzal:Nagina%40i8i$@cluster0.tnczzks.mongodb.net/caiif'
mongo = PyMongo(app)

# Check MongoDB connection
if mongo.db.client is not None:
    print("MongoDB connected successfully!")
else:
    print("Failed to connect to MongoDB.")

# Define User model



class User:
    def __init__(self, openai_key, project_name, api_cost, project_zip_binary, last_three_messages):
        self.openai_key = openai_key
        self.project_name = project_name
        self.api_cost = api_cost
        self.project_zip_binary = project_zip_binary  # Binary data
        self.created_at = datetime.now(timezone.utc)  # Using timezone-aware datetime object
        self.last_three_messages = last_three_messages  # Last three messages


    def save_to_mongo(self):
        users_collection = mongo.db.users
        existing_userProject = users_collection.find_one({
            'openai_key': self.openai_key,
            'project_array': {'$elemMatch': {'project_name': self.project_name}}
        })

        if existing_userProject:
            user_id = existing_userProject['_id']

            # If user exists, update the project_zip_binary
            users_collection.update_one(
                {'openai_key': self.openai_key},
                {
                    '$set': {
                        'project_array.$[elem].project_zip_binary': self.project_zip_binary
                    }
                },
                array_filters=[{'elem.project_name': self.project_name}],
                upsert=True
            )
            print("Zip file binary updated successfully.")
            return user_id

        existing_userApi = users_collection.find_one(
            {'openai_key': self.openai_key}
        )

        if existing_userApi:
            user_id = existing_userApi['_id']

            # If user exists, update the project_name, api_cost, and project_zip_binary
            users_collection.update_one(
                {'openai_key': self.openai_key},
                {
                    '$addToSet': {
                        'project_array': {
                            'project_name': self.project_name,
                            'api_cost': self.api_cost,
                            'project_zip_binary': self.project_zip_binary
                        }
                    }
                },
                upsert=True
            )
            return user_id

        else:
            # If user doesn't exist, create a new document
            user_data = {
                'openai_key': self.openai_key,
                'project_array': [{
                    'project_name': self.project_name,
                    'api_cost': self.api_cost,
                    'project_zip_binary': self.project_zip_binary,
                    'last_three_messages': self.last_three_messages
                }],
                'created_at': datetime.utcnow()
            }
            result = users_collection.insert_one(user_data)
            return result.inserted_id


    @staticmethod
    def exists(project_name, openai_key):
        users_collection = mongo.db.users
        existing_user = users_collection.find_one({
            'openai_key': openai_key,
            'project_array': {'$elemMatch': {'project_name': project_name}}
        })
        return existing_user is not None

    @staticmethod
    def find_by_openai_key(openai_key):
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'openai_key': openai_key})
        if user_data:
            # Convert ObjectId to string
            user_data['_id'] = str(user_data['_id'])
        return user_data

    @staticmethod
    def get_by_project_name_and_api_key(project_name, api_key):
        users_collection = mongo.db.users
        user = users_collection.find_one(
            {'project_array': {'$elemMatch': {'project_name': project_name}},
                'openai_key': api_key},
            # Projection to retrieve only the matching element of project_array
            {'project_array.$': 1}
        )

        if user and 'project_array' in user:
            return user
        else:
            return None

# def load_env_if_needed():
#     """
#     Load environment variables if the OPENAI_API_KEY is not already set.

#     This function checks if the OPENAI_API_KEY environment variable is set,
#     and if not, it attempts to load it from a .env file in the current working
#     directory. It then sets the openai.api_key for use in the application.
#     """
#     if os.getenv("OPENAI_API_KEY") is None:
#         load_dotenv()
#     if os.getenv("OPENAI_API_KEY") is None:
#         # if there is no .env file, try to load from the current working directory
#         load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
#     openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route('/')
def index():
    return render_template('index.html')


# Define messages and user_input as global variables
Messages = []
User_input = ""
aI = None
Preprompts = None
Memoryy = None
project_Name =''
Api_Key =''


@app.route('/setup_openai_key', methods=['POST'])
def setup_openai_key():
    if request.method == "POST":
        openai_key = request.form["openai_key"]
        projectname = request.form["project_type"]
        projectName = projectname.strip().replace(' ', '_')
        projectDesc = request.form["project_description"]
        improve_mode = request.form["improve_true"]
        global project_Name ,Api_Key
        Api_Key = openai_key
        project_Name=projectName
        # Get user input for modes
        # improve_mode = request.form.get("improve_mode") == "on"
        # clarify_mode = request.form.get("clarify_mode") == "on"
        # lite_mode = request.form.get("lite_mode") == "on"

        # if improve_mode:
        #     assert not (clarify_mode or lite_mode), "Clarify and lite mode are not active for improve mode"
# Check if project name and key combination already exists

        lite_mode: bool = typer.Option(
            False,
            "--lite",
            "-l",
            help="Lite mode - run only the main prompt.",
        ),
        clarify_mode: bool = typer.Option(
            True,
            "--clarify",
            "-c",
            help="Lite mode - discuss specification with AI before implementation.",
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v"),

        # Check for mode conflicts
        # if improve_mode:
        #     assert not (clarify_mode or lite_mode), "Clarify and lite mode are not active for improve mode"

        model: str = typer.Argument(
            "gpt-4-1106-preview", help="model id string"),
        temperature: float = 0.1,
        if User.exists(projectName, openai_key) and not improve_mode:
            file_name = f'{projectName}.zip'

            # Return response as JSON
            response_data = {
                'success': True,
                'file_name': file_name,
            }
            return jsonify(response_data)
        else:
            # Store the project name in the session
            session['project_name'] = projectName
            session['openai_key'] = openai_key  # Store the key in the session
            # Make a request to set the API key

            with app.test_client() as client:
                # try:
                # Send a POST request with the API key as a query parameter
                response = client.post('/setapikey?apikey=' + openai_key)
                # if there is no .env file, try to load from the current working directory
                # load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
                # openai.api_key = os.getenv("OPENAI_API_KEY")
                os.environ['OPENAI_API_KEY'] = openai_key
                openai.api_key = os.environ['OPENAI_API_KEY']
                # Process the response
                print(response.data.decode('utf-8'))
                if response.status_code == 200:

                    # Replace spaces with underscores and strip leading/trailing spaces
                    project_path = f"projects/{projectName}"

                    # Create the project directory if it doesn't exist
                    if not os.path.exists(project_path):
                        os.makedirs(project_path)
                    path = Path(project_path)
                    print("Running gpt-engineer in", path.absolute(), "\n")
                    # prompt = load_prompt(DiskMemory(path), improve_mode)
                    # Set up the AI and project configuration
                    ai = AI(
                        model_name="gpt-4-1106-preview",  # Set your desired model
                        temperature=0.1,
                        azure_endpoint="",  # Set Azure endpoint if applicable
                    )
                    logging.basicConfig(
                        level=logging.DEBUG if verbose else logging.INFO)

                    prompt = projectDesc  # Use project description as prompt

                    # Configure functions and paths
                    # configure generation function
                    if clarify_mode and not improve_mode == 'true':
                        code_gen_fn = clarified_generated
                    else:
                        code_gen_fn = gen_code
                    execution_fn = execute_entrypoint
                    improve_fn = improve

                    memory = DiskMemory(memory_path(project_path))
                    execution_env = DiskExecutionEnv()
                    agent = CliAgent.with_default_config(
                        memory,
                        execution_env,
                        ai=ai,
                        code_gen_fn=code_gen_fn,
                        improve_fn=improve_fn,
                    )

                    store = FileStore(project_path)
                    # sys.stdin = StringIO('n\n')
                    # Save the original standard input
                    # original_stdin = sys.stdin
                    # Generate or improve project
                    if improve_mode == 'true':
                        fileselector = FileSelector(projectName)
                        project_data = User.get_by_project_name_and_api_key(projectName, Api_Key)
                        project_name = project_data['project_array'][0]
                        project_zip_binary = project_name['project_zip_binary']
                        
                        if os.path.exists(project_path):
                            shutil.rmtree(project_path)
                        
                        with zipfile.ZipFile(io.BytesIO(project_zip_binary), "r") as zip_ref:
                            zip_ref.extractall(project_path)

                        file_selector = FileSelector(project_path)
                        socketio.emit('alert_received', {'msg': "Please select and deselect (add # in front) files, save it, and close it to continue..."})
                        
                        # Ensure that selected_files_dict is properly initialized
                        selected_files_dict = file_selector.ask_for_files()

                        # If selected_files_dict is not empty, proceed with further operations
                        if selected_files_dict:
                            updated_files_dict = {}

                            # Iterate over the selected files dictionary and replace double backslashes with single backslashes in the keys
                            for key, value in selected_files_dict.items():
                                updated_key = key.replace("\\\\", "/")
                                updated_files_dict[updated_key] = value
                            # Convert the regular dictionary to a FilesDict object
                        files_dict = FilesDict(updated_files_dict)
                        files_dict = agent.improve(files_dict, prompt)
                    else:
                        files_dict = agent.init(prompt)
                    # collect user feedback if user consents
                    config = (code_gen_fn.__name__, execution_fn.__name__)
                    collect_and_send_human_review(
                        prompt, model, temperature, config, agent.memory)
                    # Restore the original standard input
                    # sys.stdin = original_stdin
                    # Create a zip file in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for filename, content in files_dict.items():
                            zip_file.writestr(filename, content)
                    api_cost = ai.token_usage_log.usage_cost()

                    # Save project zip file to MongoDB
                    zip_file_binary = zip_buffer.getvalue()
                    new_user = User(openai_key, projectName,
                                    api_cost, zip_file_binary, [])
                    inserted_id = new_user.save_to_mongo()

                    if inserted_id:
                        print(f"Project zip file saved to MongoDB with ID: {inserted_id}")
                    else:
                        print("Failed to save project zip file to MongoDB.")

                    zip_buffer.close()
                        
                    if os.path.exists(project_path):
                        shutil.rmtree(project_path)                    # Create a zip file of the project directory
                    # zipf = zipfile.ZipFile(f'{projectName}.zip', 'w', zipfile.ZIP_DEFLATED)
                    # for root, dirs, files in os.walk(project_path):
                    #     for file in files:
                    #         zipf.write(os.path.join(root, file), os.path.relpath(
                    #             os.path.join(root, file), os.path.join(project_path, '..')))
                    # zipf.close()

                    print('OpenAI API key set successfully!')

                # Render the success template with necessary data
                    # return render_template('index.html', success=True,apicost='$0.002345', file_name=f'{projectName}.zip', download_url=url_for('download', file_name=f'{projectName}.zip'))
                    file_name = f'{projectName}.zip'
                    api_cost = api_cost

                    # Return response as JSON
                    response_data = {
                        'success': True,
                        'file_name': file_name,
                        'api_cost': api_cost
                    }
                    return jsonify(response_data)
                    print("OpenAI API key is set up.")
                else:
                    print("Failed to set OpenAI API key.")
                # except Exception as e:
                #     error_message = f"An error occurred: {str(e)}"
                #     print(error_message)
                    response_data = {
                        'success': False,
                    }
                    return jsonify(response_data), 500

    return render_template("index.html")


# Modify the /success route
@app.route('/success')
def success():
    # Retrieve files_dict from URL parameters
 # Retrieve files_dict from URL parameters
    files_dict_str = request.args.get('files_dict')
    # Convert string representation of dictionary into an actual dictionary
    files_dict = ast.literal_eval(files_dict_str)    # Accessing project_name and openai_key from session
    zip_buffer = io.BytesIO()
    global Messages, User_input, aI, Preprompts, Memoryy, project_Name, Api_Key

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for filename, content in files_dict.items():
            zip_file.writestr(filename, content)
    api_cost = aI.token_usage_log.usage_cost()

    # Save project zip file to MongoDB
    zip_file_binary = zip_buffer.getvalue()

    # Save the last three messages
     # Subtract the last three messages from the Messages list
    # last_three_messages = Messages[-3:]
    # Messages = Messages[:-3]

    # Convert Messages to a format suitable for MongoDB
    messages_to_save = [msg.content for msg in Messages[:-3]]  # Extract content from SystemMessage objects

    # Create a User instance with all necessary data
    new_user = User(Api_Key, project_Name, api_cost, zip_file_binary, messages_to_save)
    inserted_id = new_user.save_to_mongo()

    if inserted_id:
        print(f"Project zip file saved to MongoDB with ID: {inserted_id}")
    else:
        print("Failed to save project zip file to MongoDB.")

    zip_buffer.close()
    # Reset global variables to None or empty lists
    Messages = []
    User_input = ""
    aI = None
    Preprompts = None
    Memoryy = None

    print('OpenAI API key set successfully!')

    # Return response as JSON
    response_data = {
        'success': True,
        'file_name': f'{project_Name}.zip',
        'api_cost': api_cost
    }

    # Emit the success event with the response data
    socketio.emit('success_event', response_data)
 
    return jsonify(response_data)


@app.route('/download')
def download():
    # Retrieve project name and API key from request args
    requested_filename = request.args.get('filename')
    api_key = request.args.get('apikey')

    # Remove the ".zip" extension if it exists
    if requested_filename.endswith('.zip'):
        # Remove the last 4 characters (".zip")
        project_name = requested_filename[:-4]
    else:
        project_name = requested_filename

    # Get the user from MongoDB based on the project name and API key
    user = User.get_by_project_name_and_api_key(project_name, api_key)

    if user and 'project_array' in user and len(user['project_array']) > 0:
        # Retrieve project details
        project_name = user['project_array'][0]['project_name']
        project_zip_binary = user['project_array'][0]['project_zip_binary']

        # Set the Content-Type header for ZIP files
        return send_file(io.BytesIO(project_zip_binary), as_attachment=True, download_name=f"{project_name}.zip", mimetype='application/zip')
    else:
        return 'Project not found!'


@app.route('/setapikey', methods=['POST'])
def set_api_key():
    """
    Update the OPENAI_API_KEY in the .env file with the provided API key.
    """
    api_key = request.args.get(
        'apikey')  # Use form data instead of URL query parameters
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        openai.api_key = os.environ['OPENAI_API_KEY']

        return 'API key updated successfully!'
    else:
        return 'API key not provided!'


@app.route('/setapikeyold', methods=['POST'])
def set_api_keyold():
    """
    Update the OPENAI_API_KEY in the .env file with the provided API key.
    """
    api_key = request.args.get(
        'apikey')  # Use form data instead of URL query parameters
    if api_key:
        env_path = os.path.join(os.getcwd(), ".env")  # Path to the .env file

        # Check if the .env file exists
        if os.path.exists(env_path):
            # Read the contents of the .env file
            with open(env_path, 'r') as env_file:
                lines = env_file.readlines()

            # Find and replace the existing OPENAI_API_KEY if it exists
            with open(env_path, 'w') as env_file:
                found = False
                for line in lines:
                    if line.startswith("OPENAI_API_KEY="):
                        env_file.write(f"OPENAI_API_KEY={api_key}\n")
                        found = True
                    else:
                        env_file.write(line)
                # If the existing API key was not found, add the new one
                if not found:
                    env_file.write(f"OPENAI_API_KEY={api_key}\n")
        else:
            # If the .env file does not exist, create it and add the API key
            with open(env_path, 'w') as env_file:
                env_file.write(f"OPENAI_API_KEY={api_key}\n")

        # Reload environment variables after updating .env file
        load_dotenv(dotenv_path=env_path)
        openai.api_key = os.getenv("OPENAI_API_KEY")

        return 'API key updated successfully!'
    else:
        return 'API key not provided!'


# @app.route('/ai_question', methods=['GET'])
def ai_question(msg):
    # msg = request.args.get('msg', '')
    return render_template("index.html", msg=msg)


def clarified_generated(
    ai: AI, prompt: str, memory: BaseMemory, preprompts_holder: PrepromptsHolder
) -> FilesDict:
    """
    Generates code based on clarifications obtained from the user.

    This function processes the messages logged during the user's clarification session
    and uses them, along with the system's prompts, to guide the AI in generating code.
    The generated code is saved to a specified workspace.

    Parameters:
    - ai (AI): An instance of the AI model, responsible for processing and generating the code.
    - dbs (DBs): An instance containing the database configurations, which includes system
      and input prompts.

    Returns:
    - List[dict]: A list of message dictionaries capturing the AI's interactions and generated
      outputs during the code generation process.
    """

    preprompts = preprompts_holder.get_preprompts()
    messages: List[Message] = [SystemMessage(content=preprompts["clarify"])]
    user_input = prompt
    messages = ai.next(messages, user_input, step_name=curr_fn())
    msg = messages[-1].content.strip()
    global Messages, User_input, aI, Preprompts, Memoryy

    # Update the global ai variable
    aI = ai
    Messages = messages
    User_input = user_input
    Preprompts = preprompts
    Memoryy = memory
    if "nothing to clarify" not in msg.lower() and not msg.lower().startswith("no"):
        # If there are clarifications needed, redirect to the AI question endpoint
        # response = requests.post('/ai_question', data={'msg': msg})
        socketio.emit('msg_received', {'msg': msg})
# Return an empty response with a success status code (200)
        return '', 200
            # redirect('/ai_question?msg=' + msg)
    else:
        print("Nothing to clarify")
        # Handle the case where there's nothing to clarify
        # You might want to add additional logic here if needed
        messages = [
            SystemMessage(content=setup_sys_prompt(preprompts)),
        ] + messages[
            1:
        ]  # skip the first clarify message, which was the original clarify priming prompt
        messages = ai.next(
            messages,
            preprompts["generate"].replace(
                "FILE_FORMAT", preprompts["file_format"]),
            step_name=curr_fn(),
        )
        print()
        chat = messages[-1].content.strip()
        memory[CODE_GEN_LOG_FILE] = chat
        files_dict = chat_to_files_dict(chat)
        return files_dict


@app.route('/aiClarification', methods=['POST'])
def aiClarification():
    # Extract data from the request
    global Messages, User_input, aI, Preprompts, Memoryy
    data = request.json
    question = data.get('question')
    userAnswer = data.get('answer')

    # Modify the User_input based on the received data
    User_input = userAnswer

    if not User_input or User_input == "c":
        Messages = aI.next(
            Messages,
            "Make your own assumptions and state them explicitly before starting",
            step_name=curr_fn(),
            )
    else:
        Messages = aI.next(Messages, User_input, step_name=curr_fn())
    msg = Messages[-1].content.strip()

    if "nothing to clarify" not in msg.lower() and not msg.lower().startswith("no"):
        # If there are clarifications needed, redirect to the AI question endpoint
        # response = requests.post('/ai_question', data={'msg': msg})
        socketio.emit('msg_received', {'msg': msg})
        # redirect('/ai_question?msg=' + msg)
# Return an empty response with a success status code (200)
        return '', 200    
    else:
        print("Nothing to clarify")

        Messages = [
            SystemMessage(content=setup_sys_prompt(Preprompts)),
        ] + Messages[
            1:
        ]  # skip the first clarify message, which was the original clarify priming prompt
        Messages = aI.next(
            Messages,
            Preprompts["generate"].replace(
                "FILE_FORMAT", Preprompts["file_format"]),
            step_name=curr_fn(),
        )
        chat = Messages[-1].content.strip()
        Memoryy[CODE_GEN_LOG_FILE] = chat
        files_dict = chat_to_files_dict(chat)
        # Redirect to the /success route with necessary data
        return redirect(url_for('success', files_dict=files_dict))


@app.route('/handle_user_answer', methods=['POST'])
def handle_user_answer():
    user_answer = request.json.get('user_answer')

    # Call the clarified_generated function with the user's answer
    files_dict = clarified_generated(
        ai, user_answer, memory, preprompts_holder)

    # Check if more clarification is needed
    if additional_clarification_needed(ai, memory):
        # If more clarification is needed, send a message to the client
        socketio.emit('additional_clarification', {
                      'msg': 'Additional clarification needed'})
    else:
        # If no more clarification is needed, you can send the generated code or other information to the client
        socketio.emit('code_generated', {'files_dict': files_dict})

    return jsonify({'success': True})


def set_key(file_path, key, value):
    """
    Update the value of the specified key in the given file.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(file_path, 'w') as file:
        for line in lines:
            if line.startswith(f"{key}="):
                file.write(f"{key}={value}\n")
            else:
                file.write(line)


@app.route('/user', methods=['GET'])
def get_user_by_openai_key():
    openai_key = request.args.get('openai_key')
    if not openai_key:
        return jsonify({'error': 'openai_key parameter is required'})

    user_data = User.find_by_openai_key(openai_key)
    if user_data:
        if 'project_array' in user_data:
            # Iterate through each item in the project array
            for project in user_data['project_array']:
                # Remove the zip file binary data from each project dictionary
                if 'project_zip_binary' in project:
                    project.pop('project_zip_binary')
        return jsonify(user_data)
    else:
        return jsonify({'error': 'User not found'})


@socketio.on('message')
def handle_message(msg):
    print('Received message: ' + msg)
    # You can add additional logic here to process the received message
    # For example, you might want to call your AI function here
    # ai_question(msg)
    # Then, emit the processed message back to the clients
    socketio.emit('response', msg)


@socketio.on('connect')
def handle_connect():
    client_id = request.sid  # Get the client ID
    # Add the client ID to the set of connected clients
    connected_clients.add(client_id)
    print(f'Client {client_id} connected')


@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    # Remove the client ID from the set of connected clients
    connected_clients.remove(client_id)
    print(f'Client {client_id} disconnected')


def load_prompt(input_repo: DiskMemory, improve_mode):
    """
    Load or request a prompt from the user based on the mode.

    Parameters
    ----------
    input_repo : DiskMemory
        The disk memory object where prompts and other data are stored.
    improve_mode : bool
        Flag indicating whether the application is in improve mode.

    Returns
    -------
    str
        The loaded or inputted prompt.
    """
    if input_repo.get("prompt"):
        return input_repo.get("prompt")

    if not improve_mode:
        input_repo["prompt"] = input(
            "\nWhat application do you want gpt-engineer to generate?\n"
        )
    else:
        input_repo["prompt"] = input(
            "\nHow do you want to improve the application?\n")
    return input_repo.get("prompt")


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
    # Check if the OPENAI_API_KEY is set, if not redirect to the setup page
    print("OpenAI API key is not set. Please set it up.")
    
    # Run the application with socket connection on the specified URL