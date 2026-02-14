# AgentVANET
A decision making platform for traffic networks 


# How to Run AgentVANET Locally
Welcome to AgentVANET! This is a multi-agent AI platform that analyzes traffic and makes safe routing decisions. Follow these quick steps to get it running on your machine.

## Step 1: Install Python
Make sure you have Python (version 3.9 or higher) installed on your computer. You can download it from python.org.

## Step 2: Download the Project
Download or clone this project folder to your local machine. Open your terminal (Mac/Linux) or Command Prompt (Windows) and navigate inside the main project folder.

## Step 3: Install Required Libraries
You need to install a few Python libraries, such as langgraph and python-dotenv, for the AI orchestration and environment variables to work. Run this command in your terminal:

Bash
pip install pydantic openai langgraph python-dotenv
## Step 4: Get a Free AI API Key
This project uses Groq to run the AI reasoning models for free.

Go to the Groq Console (console.groq.com) and create a free account.

Generate a new API Key.

## Step 5: Set Up Your Environment File
You need a secure place to store your API key so the code can access it.

In the main project folder (where main.py is located), create a new text file and name it exactly .env (make sure it doesn't end in .txt).

Open the .env file and paste your API key inside like this:
GROQ_API_KEY=your_actual_api_key_here

## Step 6: Run the AI Agents!
With everything installed and your API key saved, you are ready to start the system. Run the following command in your terminal:

Bash
python main.py
You should now see the terminal print out the Traffic Agent's analysis, the Routing Agent's suggested detours, and the Safety Agent's final approval for the different traffic scenarios!
