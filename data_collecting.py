import json

class UserInfoCollector:
    """A class to collect and manage user information."""

    def __init__(self):
        self.user_info = {}

    def collect_user_info(self):
        """Collects user information and stores it in a dictionary."""
        
        # Basic Information
        self.user_info["name"] = input("Enter your name (optional): ")
        self.user_info["age_range"] = input("Enter your age range (e.g., 18-25): ")
        self.user_info["gender"] = input("Enter your gender identity (optional): ")
        self.user_info["location"] = input("Enter your general location (e.g., city, state): ")
        self.user_info["language"] = input("Enter your language: ")
        self.user_info["interests"] = input("Enter your interests/hobbies (comma-separated): ").split(",")
        self.user_info["favorites"] = input("Enter your favorite things (comma-separated): ").split(",")
        self.user_info["goals"] = input("Enter your goals/aspirations: ")
        self.user_info["communication_style"] = input("Enter your communication style (formal/informal): ")

        self.user_info["personality"] = input("Enter your personality traits (e.g., introvert, extrovert): ")
        self.user_info["values"] = input("Enter your general values/beliefs (be cautious): ")
        self.user_info["life_situation"] = input("Enter your current life situation (e.g., student, working): ")
        self.user_info["relationship_status"] = input("Enter your relationship status (optional): ")
        self.user_info["challenges"] = input("Enter any challenges/difficulties you'd like to share (optional): ")

        return self.user_info
        
    def save_user_info(self, filename="user_data.json"):
        """Saves the user information dictionary to a JSON file."""
        try:
            with open(filename, "w") as f:
                json.dump(self.user_info, f, indent=4)  # Use indent for pretty printing
            print(f"User information saved to {filename}")
        except Exception as e:  # Handle potential file errors
            print(f"Error saving user information: {e}")

# Example usage
if __name__ == "__main__":
    collector = UserInfoCollector()
    data = collector.collect_user_info()
    collector.save_user_info()
    print(data)
