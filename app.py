import streamlit as st
from hotel_receptionist import HotelReceptionist
from hotel_system import CompleteHotelSystem

# Initialize session state for persistence
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.hotel_system = CompleteHotelSystem("hotel_rooms.csv")
    st.session_state.receptionist = HotelReceptionist(st.session_state.hotel_system)
    # Add initial greeting
    st.session_state.messages.append({"role": "bot", "text": "Welcome to our hotel! I'm your AI receptionist. How may I assist you today?"})

# Streamlit Page Configuration
st.set_page_config(page_title="AI Hotel Receptionist", page_icon="🏨", layout="centered")

# Apply Dark Theme Styling
st.markdown("""
    <style>
    body {
        background-color: #121212;
        color: #ffffff;
    }
    .stTextInput, .stTextArea, .stButton>button {
        background-color: #1e1e1e !important;
        color: #ffffff !important;
    }
    .stChatMessage {
        background-color: #1e1e1e !important;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .user-message {
        text-align: right;
        color: #4CAF50;
    }
    .bot-message {
        text-align: left;
        color: #2196F3;
    }
    </style>
""", unsafe_allow_html=True)

# Chatbot Header
st.title("🤖 AI Hotel Receptionist")
st.markdown("Ask me anything about the hotel services, bookings, check-in/check-out, and more!")

# Display Chat History
for message in st.session_state.messages:
    role, text = message["role"], message["text"]
    css_class = "user-message" if role == "user" else "bot-message"
    st.markdown(f"<div class='{css_class}'>{text}</div>", unsafe_allow_html=True)

# Create a form for user input to ensure proper processing
with st.form(key="message_form", clear_on_submit=True):
    user_input = st.text_input("Type your message:", key="user_message")
    submit_button = st.form_submit_button("Send")
    
    if submit_button and user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "text": user_input})
        
        # Get AI response (force a re-run of the receptionist.get_response)
        response = st.session_state.receptionist.handle_customer_query(user_input)
        
        # Add AI response to chat history
        st.session_state.messages.append({"role": "bot", "text": response})
        
        # Force a re-run to update the UI with the new messages
        st.rerun()  # Using st.rerun() instead of st.experimental_rerun()