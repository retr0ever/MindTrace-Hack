import json

class ActionRouter:
    def __init__(self, cleaner, uncleaner, artefact_detector):
        self.cleaner = cleaner
        self.uncleaner = uncleaner
        self.artefact_detector = artefact_detector

    def route(self, action_json, current_data, original_data):
        """
        Routes SpoonOS decisions to processing modules.
        """
        command = json.loads(action_json)
        action_type = command.get("action")
        
        if action_type == "find_artefacts":
            print(f"Executing: Find {command.get('type')} artefacts")
            # Logic to call detector
            return current_data # No change to data, just reporting
            
        elif action_type == "mark_artefact":
            print(f"Executing: Mark {command.get('type')} from {command.get('start_time')} to {command.get('end_time')}")
            # Logic to mark/remove
            return current_data
            
        elif action_type == "undo_cleaning":
            print(f"Executing: Undo cleaning from {command.get('start_time')} to {command.get('end_time')}")
            return self.uncleaner.revert_cleaning(
                current_data, 
                original_data, 
                float(command.get('start_time')), 
                float(command.get('end_time')), 
                self.cleaner.fs
            )
            
        elif action_type == "alter_cleaning":
            print(f"Executing: Switch cleaning method to {command.get('method')}")
            # Logic to re-clean
            return current_data
            
        else:
            print("Unknown action")
            return current_data
