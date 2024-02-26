from flask import Flask, jsonify, render_template, redirect, session, send_file, url_for, request
import os
from pathlib import Path
import openai
import json

# Import necessary modules and classes from your CLI application
from gpt_engineer.applications.cli.cli_agent import CliAgent
from gpt_engineer.applications.cli.file_selector import FileSelector
from gpt_engineer.core.ai import AI
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.file_store import FileStore
from gpt_engineer.core.default.paths import PREPROMPTS_PATH, memory_path
from gpt_engineer.core.default.steps import execute_entrypoint, gen_code, improve
from gpt_engineer.core.preprompts_holder import PrepromptsHolder
from gpt_engineer.tools.custom_steps import clarified_gen, lite_gen, self_heal
import zipfile
from flask_pymongo import PyMongo
from datetime import datetime
from dotenv import load_dotenv
import io

app = Flask(__name__)  # creates a Flask web app
app.secret_key = 'Nim123??'  # Set a secret key for session management


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
    def __init__(self, openai_key, project_name, api_cost, project_zip_binary):
        self.openai_key = openai_key
        self.project_name = project_name
        self.api_cost = api_cost
        self.project_zip_binary = project_zip_binary  # Binary data
        self.created_at = datetime.utcnow()

    def save_to_mongo(self):
        users_collection = mongo.db.users
        existing_user = users_collection.find_one(
            {'openai_key': self.openai_key})
        if existing_user:
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
        else:
            # If user doesn't exist, create a new document
            user_data = {
                'openai_key': self.openai_key,
                'project_array': [{
                    'project_name': self.project_name,
                    'api_cost': self.api_cost,
                    'project_zip_binary': self.project_zip_binary
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
    def get_by_project_name(project_name):
        users_collection = mongo.db.users
        user = users_collection.find_one(
            {'project_array.project_name': project_name})
        return user

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


@app.route('/setup_openai_key', methods=['POST'])
def setup_openai_key():
    if request.method == "POST":
        openai_key = request.form["openai_key"]
        projectName = request.form["project_type"]
        projectDesc = request.form["project_description"]
# Check if project name and key combination already exists
        if User.exists(projectName, openai_key):
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
                 # Send a POST request with the API key as a query parameter
                response = client.post('/setapikey?apikey=' + openai_key)

                # Process the response
                print(response.data.decode('utf-8'))
                if response.status_code == 200:
                    
                    # Replace spaces with underscores and strip leading/trailing spaces
                    project_path = f"projects/{projectName.strip().replace(' ', '_')}"

                    # Create the project directory if it doesn't exist
                    if not os.path.exists(project_path):
                        os.makedirs(project_path)

                    # Set up the AI and project configuration
                    ai = AI(
                        model_name="gpt-4-1106-preview",  # Set your desired model
                        temperature=0.1,
                        azure_endpoint="",  # Set Azure endpoint if applicable
                    )

                    prompt = projectDesc  # Use project description as prompt

                    # Configure functions and paths
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

                    # Generate or improve project
                    files_dict = agent.init(prompt)

                    # Create a zip file in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for filename, content in files_dict.items():
                            zip_file.writestr(filename, content)
                    api_cost = ai.token_usage_log.usage_cost()

                    # Save project zip file to MongoDB
                    zip_file_binary = zip_buffer.getvalue()
                    new_user = User(openai_key, projectName, api_cost, zip_file_binary)
                    inserted_id = new_user.save_to_mongo()

                    if inserted_id:
                        print(f"Project zip file saved to MongoDB with ID: {
                            inserted_id}")
                    else:
                        print("Failed to save project zip file to MongoDB.")

                    zip_buffer.close()

                    # Create a zip file of the project directory
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


    return render_template("index.html")


@app.route('/success')
def success():
    if 'openai_key' in session:
        # Reload environment variables
        load_dotenv()
        apicost = session.get('api_cost')  # Retrieve project name from session
        # Retrieve project name from session
        project_name = session.get('project_name')
        project_path = f"projects/{project_name}"

        # Create a zip file of the project directory
        zipf = zipfile.ZipFile(f'{project_name}.zip',
                               'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(project_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(
                    os.path.join(root, file), os.path.join(project_path, '..')))
        zipf.close()

        print('OpenAI API key set successfully!')

# Render the success template with necessary data
        return render_template('index.html', success=True, apicost='$0.002345', file_name=f'{project_name}.zip', download_url=url_for('download', file_name=f'{project_name}.zip'))

    else:
        return redirect(url_for('index'))


@app.route('/download')
def download():
    # Retrieve project name from request args
    project_name = request.args.get('filename')

    # Remove the ".zip" extension if it exists
    if project_name.endswith('.zip'):
        project_name = project_name[:-4]  # Remove the last 4 characters (".zip")
    # Get the user from MongoDB based on the project name
    user = User.get_by_project_name(project_name)

    if user and 'project_array' in user and len(user['project_array']) > 0:
        # Retrieve the zip file binary from the first project in the project_array
        zip_file_binary = user['project_array'][0]['project_zip_binary']

        # Create a zip file in memory
        zip_buffer = io.BytesIO(zip_file_binary)
        zip_filename = f'{project_name}.zip'

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Write the zip file content directly from the binary data
            zipf.writestr(zip_filename, zip_file_binary)

        zip_buffer.seek(0)

# Set the Content-Type header for ZIP files
        return send_file(zip_buffer, as_attachment=True, download_name=zip_filename, mimetype='application/zip')
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

        # if there is no .env file, try to load from the current working directory
        load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
        openai.api_key = os.getenv("OPENAI_API_KEY")

        return 'API key updated successfully!'
    else:
        return 'API key not provided!'



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


if __name__ == "__main__":
    # Check if the OPENAI_API_KEY is set, if not redirect to the setup page
    print("OpenAI API key is not set. Please set it up.")
    print("Starting the web interface for setup...")
    app.run(debug=True, port=5000)
