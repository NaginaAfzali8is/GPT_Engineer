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
    def __init__(self, openai_key, project_name, api_cost):
        self.openai_key = openai_key
        self.project_name = project_name
        self.api_cost = api_cost
        self.created_at = datetime.utcnow()

    def save_to_mongo(self):
        users_collection = mongo.db.users
        existing_user = users_collection.find_one({
            'openai_key': self.openai_key
        })

        if existing_user:
            # If user exists, update the project_name and api_cost arrays
            users_collection.update_one(
                {'openai_key': self.openai_key},
                {
                    '$addToSet': {
                        'project_name': self.project_name,
                        'api_cost': self.api_cost
                    }
                },
                upsert=True

            )
        else:
            # If user doesn't exist, create a new document
            user_data = {
                'openai_key': self.openai_key,
                'project_name': [self.project_name],
                'api_cost': [self.api_cost],
                'created_at': self.created_at
            }
            result = users_collection.insert_one(user_data)
            return result.inserted_id

    @staticmethod
    def exists(project_name, openai_key):
        users_collection = mongo.db.users
        existing_user = users_collection.find_one({
            'openai_key': openai_key,
            'project_name': {'$elemMatch': {'$eq': project_name}}
        })
        return existing_user is not None

    @staticmethod
    def find_by_openai_key(openai_key):
        users_collection = mongo.db.users
        user_data = users_collection.find_one({'openai_key': openai_key})
        # Convert ObjectId to string
        if user_data:
            user_data['_id'] = str(user_data['_id'])
        return user_data


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
            openai.api_key = openai_key

            # Create the project directory if it doesn't exist
            project_path = f"projects/{projectName}"
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

            # if not os.path.exists(preprompts_path):
            #     os.makedirs(preprompts_path)

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

            # Store files in the project directory
            store.upload(files_dict)
            api_cost = ai.token_usage_log.usage_cost()
            api_cost = '$0.000445'
            session['api_cost'] = api_cost

            print("Project created successfully!")

            # Save project data to MongoDB
            new_user = User(openai_key, projectName, api_cost)
            inserted_id = new_user.save_to_mongo()

            if inserted_id:
                print(f"User data saved to MongoDB with ID: {inserted_id}")
            else:
                print("Failed to save user data to MongoDB.")

            project_path = f"projects/{projectName}"

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

    return render_template("index.html")


@app.route('/success')
def success():
    if 'openai_key' in session:
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
    # Get the filename from the session
    file_name = session.get('project_name')
 # Retrieve project name from session
    # project_name = session.get('project_name')
    project_name = request.args.get('filename')
    project_path = f"projects/{project_name}"

    # Define the path where you want to save the zip file
    zip_filename = f'projectsZip/{project_name}'

    # Create a zip file of the project directory
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(
                    os.path.join(root, file), os.path.join(project_path, '..')))

    # Send the zip file as an attachment
    return send_file(zip_filename, as_attachment=True)


@app.route('/user', methods=['GET'])
def get_user_by_openai_key():
    openai_key = request.args.get('openai_key')
    if not openai_key:
        return jsonify({'error': 'openai_key parameter is required'})

    user_data = User.find_by_openai_key(openai_key)
    if user_data:
        return jsonify(user_data)   
    else:
        return jsonify({'error': 'User not found'})


if __name__ == "__main__":
    # Check if the OPENAI_API_KEY is set, if not redirect to the setup page
    print("OpenAI API key is not set. Please set it up.")
    print("Starting the web interface for setup...")
    app.run(debug=True, port=5000)
