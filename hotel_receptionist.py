# hotel_receptionist.py
import pandas as pd
from langchain_ollama import OllamaLLM  # Updated import
from datetime import datetime
from hotel_system import CompleteHotelSystem

class HotelReceptionist:
    def __init__(self, hotel_system):
        self.hotel_system = hotel_system
        self.llm = OllamaLLM(model="llama3.2:1b")  # Using the updated class
        self.chat_history = []
        
        # System prompt for the AI receptionist
        self.system_prompt = (
            "You are an AI hotel receptionist. Your role is to:\n"
            "- Be polite, professional, and concise in your responses\n"
            "- Help guests with room bookings, availability checks, and information requests\n"
            "- Convert technical data into natural, friendly responses\n"
            "- Keep responses brief and to the point\n"
            "- Always maintain a helpful and welcoming tone\n\n"
            "Do not:\n"
            "- Make up information about rooms or prices\n"
            "- Give personal opinions about the hotel\n"
            "- Discuss hotel policies not mentioned in the data\n"
            "- Make promises about special requests\n"
            "- Provide information about other hotels\n\n"
            "When handling queries:\n"
            "1. Understand the guest's request\n"
            "2. Use the provided hotel data\n"
            "3. Format the response in a natural, conversational way\n"
            "4. Keep the interaction professional and efficient\n\n"
            "Example format for responses:\n"
            "\"We have [number] [room type] rooms available at $[price] per night.\"\n"
            "\"Our [room type] rooms feature [amenities] and are priced at $[price] per night.\""
        )
    
    def get_response(self, user_input: str) -> str:
        """Processes user input and returns a response."""

        if "book" in user_input.lower():
            return self.handle_booking_request(user_input)
        elif "check-in" in user_input.lower():
            return self.handle_checkin_request(user_input)
        elif "check-out" in user_input.lower():
            return self.handle_checkout_request(user_input)
        elif "rooms" in user_input.lower():  # Redirect to a generic query handler
            return self.handle_customer_query(user_input)
        else:
            return "I can help you with bookings, check-in/out, and room information. How can I assist you today?"


    def handle_room_inquiry(self, user_input):
        return self.hotel_system.process_user_query(user_input)['message']



    def save_to_chat_history(self, speaker, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.chat_history.append({
            "timestamp": timestamp,
            "speaker": speaker,
            "message": message
        })

    def generate_llm_response(self, hotel_data, user_query):
        # Combine the system prompt with the query and hotel data for context
        prompt = (
            f"{self.system_prompt}\n\n"
            f"User query: \"{user_query}\"\n"
            f"Hotel Data: \"{hotel_data}\"\n\n"
            "Please provide a natural, concise response as a hotel receptionist. "
            "Keep the response brief and friendly."
        )
        
        try:
            response = self.llm.invoke(prompt)
            # Trim the response to roughly 50 words
            response = ' '.join(response.split()[:50])
            return response
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error in LLM invoke: {e}")
            # Fallback: Return hotel data or a default message
            return hotel_data if hotel_data else "I apologize, but I'm having trouble processing your request. How else may I assist you?"

    def handle_customer_query(self, user_input):
        # Save customer input to history
        self.save_to_chat_history("Customer", user_input)
        
        # Get response from the hotel system (a dictionary with at least a 'message' key)
        hotel_response = self.hotel_system.process_user_query(user_input)
        
        # Generate a natural language response using the LLM
        ai_response = self.generate_llm_response(hotel_response['message'], user_input)
        
        # Save AI response to history
        self.save_to_chat_history("AI", ai_response)
        
        return ai_response

    def start_conversation(self):
        greeting = "Welcome to our hotel! I'm your AI receptionist. How may I assist you today?"
        self.save_to_chat_history("AI", greeting)
        print(f"AI: {greeting}")

        while True:
            user_input = input("Customer: ").strip()
            
            if user_input.lower() in ['exit', 'bye', 'goodbye']:
                farewell = "Thank you for choosing our hotel. Have a great day!"
                self.save_to_chat_history("AI", farewell)
                print(f"AI: {farewell}")
                break

            print("AI: Let me check that for you...")
            response = self.handle_customer_query(user_input)
            print(f"AI: {response}")

def main():
    
    # Point to the CSV file instead of a DB file
    hotel_system = CompleteHotelSystem("hotel_rooms.csv")
    receptionist = HotelReceptionist(hotel_system)
    receptionist.start_conversation()

if __name__ == "__main__":
    main()
