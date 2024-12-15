import streamlit as st 
import requests
import pandas as pd
import time

BLAND_API_KEY = 'org_8eabc93849311b46844d2ff69b684f544bf7adb1ed6a4b93b328e92791bfa79e1909301b43eadc679bde69'
GROK_API_KEY = 'xai-CDqxS2N84swMdjSuYJFiqLs6jl1zqOgbpNBG8JmXJ7LXxeNQ0ziRylXX9mcs6o5i3eo720x1CdMwjsTa'

# Mock user credentials for authentication
USER_CREDENTIALS = {
    "admin": "password123",
    "user1": "pass456"
}

# File for citizen data (already uploaded)
FILE_PATH = r'data/New_Jersey_Insurance_Residents_With_SSN.xlsx'

def process_citizen_data(file_path):
    """
    Reads citizen data from an Excel file and processes it for eGovConnect usage.
    """
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        raise Exception(f"Error reading Excel file: {e}")

import requests
import pandas as pd

def call_grok_api(ssn, citizen_data):
    """
    Function to call the Grok API with an SSN and retrieve detailed citizen information.
    """
    # Retrieve the row corresponding to the SSN
    citizen_row = citizen_data[citizen_data['SSN'] == ssn]
    
    if citizen_row.empty:
        raise ValueError(f"No data found for SSN: {ssn}")

    # Convert the entire row to a dictionary
    citizen_info = citizen_row.iloc[0].to_dict()
    
    print("Citizen Info:", citizen_info)

    # Create a prompt that includes all relevant citizen information
    # prompt = f"Provide detailed information for the following citizen:\n{citizen_info}"
    
    # Extract relevant details for the prompt
    insurance_plan_type = citizen_info.get('Insurance Plan Type', 'N/A')
    insurance_provider = citizen_info.get('Insurance Provider', 'N/A')
    coverage_level = citizen_info.get('Coverage Level', 'N/A')

    hospital_details = (
        f"Hospital Name: {citizen_info.get('Hospital 1 Name', 'N/A')}\n"
        f"Location: {citizen_info.get('Hospital 1 Location', 'N/A')}\n"
        f"Type: {citizen_info.get('Hospital 1 Type', 'N/A')}\n"
        f"Insurance Coverage: {citizen_info.get('Hospital 1 Insurance Coverage', 'N/A')}\n"
        f"Contact Number: {citizen_info.get('Hospital 1 Contact Number', 'N/A')}\n"
        f"Rating: {citizen_info.get('Hospital 1 Rating', 'N/A')}"
    )

    clinic_details = (
        f"Clinic Name: {citizen_info.get('Clinic 1 Name', 'N/A')}\n"
        f"Location: {citizen_info.get('Clinic 1 Location', 'N/A')}\n"
        f"Type: {citizen_info.get('Clinic 1 Type', 'N/A')}\n"
        f"Insurance Coverage: {citizen_info.get('Clinic 1 Insurance Coverage', 'N/A')}\n"
        f"Contact Number: {citizen_info.get('Clinic 1 Contact Number', 'N/A')}\n"
        f"Rating: {citizen_info.get('Clinic 1 Rating', 'N/A')}"
    )

    # Create a prompt that includes all relevant information
    prompt = (
        f"Provide detailed information based on the following:\n"
        f"Insurance Plan Type: {insurance_plan_type}\n"
        f"Insurance Provider: {insurance_provider}\n"
        f"Coverage Level: {coverage_level}\n\n"
        f"{hospital_details}\n\n"
        f"{clinic_details}"
    )
    
    print("Prompt:", prompt)

    # Set up the API call
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROK_API_KEY}"
    }
    
    data = {
        "messages": [
            {"role": "system", "content": "You are an AI-powered government service assistant."},
            {"role": "user", "content": prompt}
        ],
        "model": "grok-beta",
        "stream": False,
        "temperature": 0
    }

    # Make the API request
    response = requests.post(url, headers=headers, json=data)
    
    # Handle the response
    if response.status_code == 200:
        return response.json()  # Return the full response from Grok
    else:
        raise Exception(f"Grok API Error: {response.status_code} - {response.text}")


def get_call_details(call_id):
    """
    Poll the eGovConnect for call details and extract name and SSN from the caller's response.
    """
    url = "https://api.bland.ai/logs"
    data = {"call_id": call_id}
    
    retries = 10
    delay = 15

    for attempt in range(retries):
        st.write(f"Attempting to fetch call details for call ID: {call_id} (Attempt {attempt + 1} of {retries})")
        try:
            response = requests.post(url, json=data, headers={"Authorization": f"Bearer {BLAND_API_KEY}", "Content-Type": "application/json"})
            call_details = response.json()
            call_status = call_details.get('queue_status', '').lower()

            if call_status in ['complete', 'completed']:
                st.write("Call is complete. Returning details.")
                # Extract name and SSN from the logs or response
                # Assuming the API response contains a 'name' and 'ssn' field
                name = call_details.get("caller_name")
                ssn = call_details.get("caller_ssn")

                if name and ssn:
                    st.write(f"Caller Name: {name}")
                    st.write(f"Caller SSN: {ssn}")
                else:
                    st.error("Failed to extract name and SSN from call details.")

                return call_details

        except Exception as e:
            st.error(f"Error fetching call details: {e}")

        st.write(f"Call status: {call_status}. Retrying in {delay} seconds...")
        time.sleep(delay)

    st.error("Call did not complete within the allowed attempts.")
    return None

def initiate_bland_call(phone_number):
    """
    Initiates a call to the caller to collect name and SSN.
    """
    task_script = (
       "Hello, welcome to your eGovConnect assistant. Please say your full name followed by your Social Security Number. "
        "We will use this information to locate your records in our system."
    )

    data = {
        "phone_number": phone_number,
        "task": task_script,
        "summarize": True,
        "record": True
    }

    headers = {"Authorization": f"Bearer {BLAND_API_KEY}", "Content-Type": "application/json"}

    response = requests.post("https://api.bland.ai/call", json=data, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        call_id = response_data.get("call_id")
        st.write("Call initiated successfully!")

        return call_id
    else:
        st.error(f"Failed to initiate call: {response.status_code} - {response.text}")
        return None

def handle_post_call_actions(response_content, name):
    """
    Handles further actions like changing insurance details or booking a meeting.
    """
    st.write(f"Response provided to {name}: {response_content}")
    st.write("Further options: \n1. Change insurance coverage, provider, or plan \n2. Book a clinic meeting")

def login_page():
    """
    Displays the login page and validates user credentials.
    """
    st.title("eGovConnect Login")

    if not st.session_state.get("logged_in", False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"Welcome {username}!")
                dashboard()
                st.rerun()
                st.session_state.rerun = True
            else:
                st.error("Invalid username or password.")
    
def dashboard():   
   
    st.sidebar.checkbox("Medicare & Medicaid Services")
    st.sidebar.checkbox("Taxpayer Identification Number")
    st.sidebar.checkbox("Veterans Affairs")
    st.sidebar.checkbox("Employment and Training Administration")
    
    """
    Displays the dashboard after user login.
    """
    st.markdown("""
    <style>
    .main-title {
        font-family: 'Arial', sans-serif;
        color: #2E86C1;
        font-size: 36px;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .sub-header {
        font-family: 'Verdana', sans-serif;
        color: #2C3E50;
        font-size: 24px;
        margin-top: 20px;
    }
    .footer {
        font-family: 'Courier New', monospace;
        color: #7D3C98;
        font-size: 14px;
        text-align: center;
        margin-top: 40px;
    }
    </style>
    <div class="main-title">eGovConnect Dashboard</div>
    """, unsafe_allow_html=True)

    phone_number = st.text_input("Phone Number")
    if st.button("Initiate Call"):
        try:
            citizen_data = process_citizen_data(FILE_PATH)
            call_id = initiate_bland_call(phone_number)

            if call_id:
                st.write("Polling for call status...")

                call_details = get_call_details(call_id)

                if call_details:
                    st.markdown("<div class='sub-header'>Call Details</div>", unsafe_allow_html=True)
                    st.json(call_details)

                    caller_name = call_details.get("caller_name")  # From call logs
                    ssn = call_details.get("caller_ssn")           # From call logs

                    if caller_name and ssn:
                        ai_response, name = call_grok_api(ssn, citizen_data)
                        response_content = ai_response['choices'][0]['message']['content']

                        handle_post_call_actions(response_content, name)
                    else:
                        st.error("Failed to retrieve caller's name and SSN.")
                else:
                    st.error("Failed to retrieve complete call details.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("<div class='footer'>© 2024 eGovConnect. All Rights Reserved.</div>", unsafe_allow_html=True)

def logout():
    """
    Logs out the user and resets the session state.
    """
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.rerun()

def main():
    """
    Main function to manage login and dashboard display.
    """
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = None

    if not st.session_state["logged_in"]:
        st.sidebar.title("Configuration")
        st.sidebar.text('user1')
        st.sidebar.text('pass456')
                
        
    if st.session_state["logged_in"]:
        st.sidebar.write(f"Logged in as: {st.session_state['username']}")
        st.sidebar.button("Logout", on_click=logout)
        dashboard()
    else:
        login_page()

if __name__ == "__main__":
    main()