# hotel_system.py
import pandas as pd
from sqlalchemy import create_engine, text

class CompleteHotelSystem:
    def __init__(self, data_source):
        # Validate data source
        if not data_source:
            raise ValueError("Data source path is required.")
        
        # If a CSV file is provided, load it into an in-memory SQLite database
        if data_source.endswith(".csv"):
            self.engine = create_engine('sqlite:///:memory:')
            try:
                df = pd.read_csv(data_source)
                
                # Validate required columns
                required_columns = ['id', 'type', 'price', 'availability']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    raise ValueError(f"CSV file is missing required columns: {missing_columns}")
                
                # Ensure data types are correct
                df['id'] = df['id'].astype(int)
                df['price'] = df['price'].astype(float)
                df['availability'] = df['availability'].astype(str)
                
                # Load data into SQLite
                df.to_sql('rooms', self.engine, if_exists='replace', index=False)
                
            except Exception as e:
                raise ValueError(f"Error loading CSV file: {str(e)}")
        else:
            # Otherwise, assume it's a SQLite database file
            self.engine = create_engine(f'sqlite:///{data_source}')
        
        self.current_booking = None
        
    def execute_query(self, query, params=None):
        """Execute a SQL query and return results"""
        with self.engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            return result.fetchall()

    def execute_update(self, query, params=None):
        """Execute an update query within a transaction"""
        with self.engine.begin() as conn:
            if params:
                conn.execute(text(query), params)
            else:
                conn.execute(text(query))

    def get_query_by_type(self, query_type):
        """Return the appropriate SQL query based on query type"""
        queries = {
            # 1. Availability Queries
            "check_all_availability": """
                SELECT type, COUNT(*) as available_rooms, price
                FROM rooms 
                WHERE availability = 'Available'
                GROUP BY type, price
                ORDER BY price;
            """,
            "check_specific_room_type": """
                SELECT id, price
                FROM rooms
                WHERE type = :room_type 
                AND availability = 'Available';
            """,
            # 2. Price Queries
            "price_range": """
                SELECT type, price, COUNT(*) as room_count
                FROM rooms
                WHERE availability = 'Available'
                AND price BETWEEN :min_price AND :max_price
                GROUP BY type, price
                ORDER BY price;
            """,
            "cheapest_available": """
                SELECT type, price
                FROM rooms
                WHERE availability = 'Available'
                ORDER BY price ASC
                LIMIT 1;
            """,
            # 3. Room Features
            "room_features": """
                SELECT type, price,
                    CASE 
                        WHEN type = 'Suite' THEN 'King bed, living area, mini bar, workspace'
                        WHEN type = 'Double' THEN 'Two queen beds, workspace'
                        WHEN type = 'Single' THEN 'One queen bed, workspace'
                    END as features
                FROM rooms
                WHERE availability = 'Available'
                GROUP BY type, price;
            """,
            # 4. Comprehensive Room Info
            "all_room_info": """
                SELECT 
                    r.type,
                    r.price,
                    COUNT(*) as available_rooms,
                    CASE 
                        WHEN r.type = 'Suite' THEN 'King bed, living area, mini bar, workspace'
                        WHEN r.type = 'Double' THEN 'Two queen beds, workspace'
                        WHEN r.type = 'Single' THEN 'One queen bed, workspace'
                    END as features,
                    CASE 
                        WHEN r.type = 'Suite' THEN 4
                        WHEN r.type = 'Double' THEN 2
                        WHEN r.type = 'Single' THEN 1
                    END as max_occupancy
                FROM rooms r
                WHERE r.availability = 'Available'
                GROUP BY r.type, r.price
                ORDER BY r.price;
            """
        }
        return queries.get(query_type, "")

    def book_room(self, room_id):
        """Update room status to booked"""
        query = """
            UPDATE rooms 
            SET availability = 'Booked' 
            WHERE id = :room_id;
        """
        self.execute_update(query, {"room_id": room_id})

    def process_user_query(self, user_input):
        """Process natural language queries and handle requests"""
        user_input = user_input.lower()
        
        try:
            # 1. Handle Booking Requests
            if 'book' in user_input:
                room_types = {'single': 'Single', 'double': 'Double', 'suite': 'Suite'}
                requested_type = next((room_types[rt] for rt in room_types if rt in user_input), None)
                
                if requested_type:
                    results = self.execute_query(
                        self.get_query_by_type("check_specific_room_type"),
                        {"room_type": requested_type}
                    )
                    
                    if results:
                        room_id, price = results[0]
                        self.current_booking = {
                            'room_id': room_id,
                            'room_type': requested_type,
                            'price': price
                        }
                        return {
                            'action': 'booking_request',
                            'message': f"I found a {requested_type} room available for ${price:.2f} per night. Would you like to confirm this booking? (yes/no)"
                        }
                    else:
                        return {
                            'action': 'error',
                            'message': f"I apologize, but there are no {requested_type} rooms available at the moment."
                        }
                else:
                    return {
                        'action': 'error',
                        'message': "What type of room would you like to book? (Single, Double, or Suite)"
                    }
            
            # 2. Handle Booking Confirmation
            elif user_input in ['yes', 'confirm', 'okay', 'sure'] and self.current_booking:
                self.book_room(self.current_booking['room_id'])
                response = (f"Great! I've booked your {self.current_booking['room_type']} room. "
                            f"The total cost is ${self.current_booking['price']:.2f} per night. "
                            "Thank you for choosing our hotel!")
                self.current_booking = None
                return {'action': 'confirmed', 'message': response}
            
            # 3. Handle Booking Cancellation
            elif user_input in ['no', 'cancel']:
                self.current_booking = None
                return {
                    'action': 'cancel',
                    'message': "Booking cancelled. Is there anything else I can help you with?"
                }
            
            # 4. Handle Availability Queries
            elif any(word in user_input for word in ['available', 'vacancy', 'free']):
                if any(rt in user_input for rt in ['single', 'double', 'suite']):
                    room_type = next(rt for rt in ['Single', 'Double', 'Suite'] if rt.lower() in user_input)
                    results = self.execute_query(
                        self.get_query_by_type("check_specific_room_type"),
                        {"room_type": room_type}
                    )
                    available_count = len(results)
                    if available_count > 0:
                        return {
                            'action': 'info',
                            'message': f"Yes, we have {available_count} {room_type} room(s) available at ${results[0][1]:.2f} per night."
                        }
                    else:
                        return {
                            'action': 'info',
                            'message': f"Sorry, there are no available {room_type} rooms at the moment."
                        }
                else:
                    results = self.execute_query(self.get_query_by_type("check_all_availability"))
                    if results:
                        available_rooms = [f"{r[0]}: {r[1]} room(s) at ${r[2]:.2f}" for r in results]
                        return {
                            'action': 'info',
                            'message': "Available rooms:\n" + "\n".join(available_rooms)
                        }
                    else:
                        return {
                            'action': 'info',
                            'message': "Sorry, there are no available rooms at the moment."
                        }
            
            # 5. Handle Price Queries
            elif any(word in user_input for word in ['price', 'cost', 'rate', 'cheap']):
                if 'cheapest' in user_input:
                    results = self.execute_query(self.get_query_by_type("cheapest_available"))
                    if results:
                        return {
                            'action': 'info',
                            'message': f"Our most economical option is a {results[0][0]} room at ${results[0][1]:.2f} per night."
                        }
                else:
                    results = self.execute_query(self.get_query_by_type("room_features"))
                    if results:
                        price_info = [f"{r[0]} (${r[1]:.2f}): {r[2]}" for r in results]
                        return {
                            'action': 'info',
                            'message': "Room prices and features:\n" + "\n".join(price_info)
                        }
            
            # 6. Handle Feature Queries
            elif any(word in user_input for word in ['feature', 'amenity', 'include']):
                results = self.execute_query(self.get_query_by_type("room_features"))
                if results:
                    features = [f"{r[0]} (${r[1]:.2f}): {r[2]}" for r in results]
                    return {
                        'action': 'info',
                        'message': "Room features:\n" + "\n".join(features)
                    }
            
            # 7. Handle General Information Request
            elif 'info' in user_input or 'detail' in user_input:
                results = self.execute_query(self.get_query_by_type("all_room_info"))
                if results:
                    info = [
                        f"{r[0]} - ${r[1]:.2f}/night\n"
                        f"  Available: {r[2]} room(s)\n"
                        f"  Features: {r[3]}\n"
                        f"  Max Occupancy: {r[4]} people"
                        for r in results
                    ]
                    return {
                        'action': 'info',
                        'message': "Room Details:\n" + "\n".join(info)
                    }
            
            # 8. Default Response
            return {
                'action': 'info',
                'message': ("How can I help you today? You can ask about:\n"
                            "- Room availability\n"
                            "- Room prices and features\n"
                            "- Book a room\n"
                            "- Room details and information")
            }

        except Exception as e:
            return {
                'action': 'error',
                'message': f"I apologize, but I encountered an error: {str(e)}"
            }

def main():
    try:
        hotel_system = CompleteHotelSystem("hotel_rooms.csv")
        
        print("Welcome to Hotel Booking Assistant!")
        print("You can:\n"
              "- Check room availability\n"
              "- Get price information\n"
              "- Learn about room features\n"
              "- Book a room\n"
              "- Get detailed information\n"
              "(Type 'exit' to quit)")
        
        while True:
            user_input = input("\nGuest: ").strip()
            if user_input.lower() == 'exit':
                print("\nThank you for using our Hotel Booking Assistant. Have a great day!")
                break
            
            response = hotel_system.process_user_query(user_input)
            print(f"\nAssistant: {response['message']}")

    except Exception as e:
        print(f"Error initializing the system: {str(e)}")

if __name__ == "__main__":
    main()