#!/usr/bin/env python3
"""
The Spirit of the Lehua Tree - Text Adventure Game
"""

import time
import sys
import os
import random
import enum
import json
from typing import List, Dict, Any, Optional, Tuple
import openai
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class SceneType(enum.Enum):
    """Enum for different scene types in the game."""
    INTRO = "intro"
    SCENE_1 = "scene_1"
    SCENE_1_MORE_INFO = "scene_1_more_info"
    SCENE_2_RIDGE = "scene_2_ridge"
    SCENE_2_LAVA = "scene_2_lava"
    SCENE_3 = "scene_3"
    SCENE_3_NEGOTIATE = "scene_3_negotiate"
    FINAL_RESTORE = "final_scene_restore"
    FINAL_SHATTER = "final_scene_shatter"
    FINAL_NEGOTIATE = "final_scene_negotiate"
    END = "end"

class CharacterType(enum.Enum):
    """Enum for different character types in the game."""
    HOST = "HOST"
    AHI = "AHI"
    MOO_WAHINE = "MOʻO WAHINE"
    NIGHT_FOG_SPIRIT = "NIGHT FOG SPIRIT"
    MENEHUNE = "MENEHUNE"
    PLAYER = "KEOLA"
    NONE = ""

class ChoiceCategory(enum.Enum):
    """Enum for different choice categories in the game."""
    PATH = "path"
    ANSWER = "answer"
    ACTION = "action"
    NEGOTIATION = "negotiation"
    PLAY_AGAIN = "play_again"

class EndingType(enum.Enum):
    """Enum for different ending types in the game."""
    RESTORATION = "Restoration"
    SACRIFICE = "Sacrifice"
    HARMONY = "Harmony"
    UNKNOWN = "Unknown"

class TextAdventureGame:
    def __init__(self):
        """Initialize the game with starting state and story content."""
        self.player_name = "Keola"
        self.current_scene = SceneType.INTRO
        self.game_state = {
            "visited_locations": set(),
            "inventory": [],
            "choices_made": {},
            "relationships": {},
            "game_over": False
        }
        
        # Define typing speed (characters per second)
        self.typing_speed = 50
        
        # Track story progression
        self.story_progress = 0
        
        # Initialize OpenAI client
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables.")
            print("You'll need to set this for the LLM functionality to work.")
            print("For now, the game will fall back to numbered choices.")
            self.use_llm = False
        else:
            self.client = openai.OpenAI(api_key=self.openai_api_key)
            self.use_llm = True
        
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def slow_print(self, text, speed_factor=1.0):
        """Print text with a typewriter effect."""
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(1.0 / (self.typing_speed * speed_factor))
        print()
        
    def print_dialogue(self, speaker: CharacterType, text: str, speed_factor=1.0):
        """Print character dialogue with speaker name."""
        speaker_display = f"{speaker.value}: " if speaker != CharacterType.NONE else ""
        self.slow_print(f"{speaker_display}{text}", speed_factor)
        
    def print_narration(self, text: str, speed_factor=1.0):
        """Print narration text."""
        self.slow_print(text, speed_factor)
        
    def print_scene_description(self, text: str):
        """Print scene description with formatting."""
        print("\n" + "=" * 80)
        self.slow_print(text, 1.5)
        print("=" * 80 + "\n")
    
    def process_user_input_with_llm(self, user_input: str, options: List[str], category: ChoiceCategory) -> int:
        """
        Use OpenAI's LLM to determine which option the user's free-form input corresponds to.
        
        Args:
            user_input: The free-form text input from the user
            options: List of available options
            category: The category of choice being made
            
        Returns:
            Integer representing the chosen option (1-based index)
        """
        try:
            # Construct the prompt for the LLM
            prompt = f"""
            In a text adventure game, the user has been presented with the following options:
            
            {', '.join(f'{i+1}. {option}' for i, option in enumerate(options))}
            
            The user responded with: "{user_input}"
            
            Based on their response, which option (1 to {len(options)}) did they choose? 
            Respond with just the number of the best matching option.
            """
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that determines which predefined option a user's free-form text response corresponds to in a text adventure game."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            # Extract the choice number from the response
            choice_text = response.choices[0].message.content.strip()
            
            # Try to extract a number from the response
            for word in choice_text.split():
                if word.isdigit() and 1 <= int(word) <= len(options):
                    return int(word)
            
            # If we couldn't extract a valid number, default to the first option
            return 1
            
        except Exception as e:
            print(f"\nError processing input with LLM: {e}")
            print("Falling back to numbered choice selection.")
            return self.get_numbered_choice(options)
    
    def get_numbered_choice(self, options: List[str]) -> int:
        """Get user choice using numbered options as fallback."""
        while True:
            try:
                choice = input("\nEnter your choice (number): ")
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    return choice_num
                else:
                    print(f"Please enter a number between 1 and {len(options)}.")
            except ValueError:
                print("Please enter a valid number.")
    
    def get_user_choice(self, options: List[str], category: ChoiceCategory) -> int:
        """
        Present options to the user and get their choice using free-form text or numbers.
        
        Args:
            options: List of available options
            category: The category of choice being made
            
        Returns:
            Integer representing the chosen option (1-based index)
        """
        print("\nWhat will you do?")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        if self.use_llm:
            print("\nDescribe your choice in your own words:")
            user_input = input("> ")
            return self.process_user_input_with_llm(user_input, options, category)
        else:
            return self.get_numbered_choice(options)
                
    def update_game_state(self, scene: SceneType, choice: Optional[int] = None):
        """Update the game state based on the current scene and choice."""
        self.game_state["visited_locations"].add(scene.value)
        
        if choice is not None:
            self.game_state["choices_made"][scene.value] = choice
            
        # Update story progression
        self.story_progress += 1
        
    def intro_scene(self) -> SceneType:
        """Display the introduction scene."""
        self.clear_screen()
        self.print_scene_description("[Opening - Calm ocean sounds, soft ukulele playing in background]")
        
        self.print_dialogue(CharacterType.HOST, "Aloha, traveler. Tonight, we walk the path between worlds—where mountains breathe, waves speak, and spirits remember. You are Keola, a young guardian in training, chosen by the forest goddess Laka to protect the sacred island of Moku Huna.", 1.2)
        time.sleep(1)
        self.print_dialogue(CharacterType.HOST, "But something ancient has awakened in the valleys. The winds no longer sing, and the lehua trees are weeping red blossoms before their time. The spirit of the island is calling you… Will you answer?", 1.2)
        time.sleep(1)
        self.print_dialogue(CharacterType.HOST, "Let's begin.", 1.2)
        
        input("\nPress Enter to continue...")
        self.update_game_state(SceneType.INTRO)
        return SceneType.SCENE_1
        
    def scene_1(self) -> SceneType:
        """Display Scene 1 and handle user choice."""
        self.clear_screen()
        self.print_scene_description("[Scene 1 – Deep Forest, Morning Birds Chirping]")
        
        self.print_dialogue(CharacterType.HOST, "You arrive at the base of the Wailoa Valley, where mist curls around giant ferns and the scent of guava clings to the breeze. At the center of a clearing stands your guide—Ahi, a talking pueo, or Hawaiian owl.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "Keola, the heart of the forest is fading. The Night Fog Spirit has stolen the seed stone from the mother lehua tree. Without it, balance will unravel.", 0.8)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.AHI, "You must retrieve it before moonrise.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "Ahi points to two paths: one climbs the windy ridge to the cliffs, the other descends into a lava tube that winds beneath the forest floor.", 1.2)
        time.sleep(0.5)
        
        options = [
            "Climb the ridge to search from above.",
            "Enter the lava tube and follow the underground river.",
            "Ask Ahi for more information before deciding." # Additional option for flexibility
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.PATH)
        self.update_game_state(SceneType.SCENE_1, choice)
        
        if choice == 1:
            return SceneType.SCENE_2_RIDGE
        elif choice == 2:
            return SceneType.SCENE_2_LAVA
        else:
            return SceneType.SCENE_1_MORE_INFO
            
    def scene_1_more_info(self) -> SceneType:
        """Additional scene for more information from Ahi."""
        self.clear_screen()
        self.print_dialogue(CharacterType.HOST, "You decide to ask Ahi for more information before making your choice.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "The ridge path is faster but exposed to the elements and perhaps watchful eyes. The lava tube is ancient and protected by guardians who test those who enter.", 0.8)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.AHI, "Choose wisely, for each path reveals different aspects of the island's spirit.", 0.8)
        time.sleep(0.5)
        
        options = [
            "Climb the ridge to search from above.",
            "Enter the lava tube and follow the underground river."
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.PATH)
        self.update_game_state(SceneType.SCENE_1_MORE_INFO, choice)
        
        if choice == 1:
            return SceneType.SCENE_2_RIDGE
        else:
            return SceneType.SCENE_2_LAVA
            
    def scene_2_ridge(self) -> SceneType:
        """Display Scene 2 (Ridge Path) and handle user choice."""
        self.clear_screen()
        self.print_scene_description("[Scene 2 – Windy Ridge, Overlooking the Valley]")
        
        self.print_dialogue(CharacterType.HOST, "The climb is steep, but the view from the ridge reveals the island's secrets. You can see the pattern of the forest below, where a dark mist gathers unnaturally in one area.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "As you follow the ridge, a strong gust nearly knocks you off balance. A menehune—a small forest guardian—appears from behind a rock.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.MENEHUNE, "The high path shows much but protects little. To find what you seek, you must answer: What guides the lost traveler home?", 0.8)
        time.sleep(0.5)
        
        options = [
            "The stars above.",
            "The memory of where they came from.",
            "The help of those they meet along the way."
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.ANSWER)
        self.update_game_state(SceneType.SCENE_2_RIDGE, choice)
        
        if choice == 3:
            self.print_dialogue(CharacterType.MENEHUNE, "Wise answer. No journey is truly alone. Look there—the dark mist parts to reveal a hidden cave entrance.", 0.8)
        else:
            self.print_dialogue(CharacterType.MENEHUNE, "A good thought, but incomplete. Remember that no journey is truly alone. Still, I will help you—look there, where the dark mist gathers.", 0.8)
        
        time.sleep(1)
        return SceneType.SCENE_3
        
    def scene_2_lava(self) -> SceneType:
        """Display Scene 2 (Lava Tube) and handle user choice."""
        self.clear_screen()
        self.print_scene_description("[Scene 2 – Underground Lava Tube, Dripping Water Echoes]")
        
        self.print_dialogue(CharacterType.HOST, "The lava tube is narrow and pulsing with ancient energy. As your footsteps echo through the dark, you hear soft chanting… a ghostly mele. Suddenly, glowing red eyes appear. A moʻo wahine—a guardian lizard spirit—emerges.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.MOO_WAHINE, "Why do you walk the bones of this mountain, child? Only those who carry truth may pass.", 0.8)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.MOO_WAHINE, "Answer me this, and I shall let you through: What gives the lehua tree its strength—its blossoms, its roots, or its kin?", 0.8)
        time.sleep(0.5)
        
        options = [
            "Its blossoms.",
            "Its roots.",
            "Its kin."
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.ANSWER)
        self.update_game_state(SceneType.SCENE_2_LAVA, choice)
        
        if choice == 3:
            self.print_dialogue(CharacterType.MOO_WAHINE, "Well spoken. The lehua thrives not alone, but with the land, the wind, the rain, and the hearts who remember her. Go in peace.", 0.8)
        else:
            self.print_dialogue(CharacterType.MOO_WAHINE, "Not quite. The lehua thrives not alone, but with the land, the wind, the rain, and the hearts who remember her. Remember this wisdom as you continue.", 0.8)
        
        time.sleep(1)
        return SceneType.SCENE_3
        
    def scene_3(self) -> SceneType:
        """Display Scene 3 and handle user choice."""
        self.clear_screen()
        self.print_scene_description("[Scene 3 – Secret Chamber, Drumming in the Distance]")
        
        self.print_dialogue(CharacterType.HOST, "You emerge into a hidden chamber filled with glowing carvings and the scent of plumeria. In the center lies the stolen seed stone, pulsing with life.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "But before you can grab it, the Night Fog Spirit forms before you—mist shaped like a serpent, eyes like black pearls.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.NIGHT_FOG_SPIRIT, "This stone is no longer yours. Leave now, or be forgotten like the rest.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "You must act quickly. Ahi lands beside you.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "You can restore the stone through chant and light, or shatter it to sever its power forever. But know this: one heals the island… the other saves only you.", 0.8)
        time.sleep(0.5)
        
        options = [
            "Chant the ancient prayer and restore the seed stone.",
            "Shatter the stone to banish the spirit, risking the island's balance.",
            "Try to negotiate with the Night Fog Spirit." # Additional option for flexibility
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.ACTION)
        self.update_game_state(SceneType.SCENE_3, choice)
        
        if choice == 1:
            return SceneType.FINAL_RESTORE
        elif choice == 2:
            return SceneType.FINAL_SHATTER
        else:
            return SceneType.SCENE_3_NEGOTIATE
            
    def scene_3_negotiate(self) -> SceneType:
        """Additional scene for negotiating with the Night Fog Spirit."""
        self.clear_screen()
        self.print_dialogue(CharacterType.HOST, "You step forward, facing the Night Fog Spirit directly.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.PLAYER, "Why have you taken the seed stone? Perhaps we can find another way to address your needs without harming the island.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.NIGHT_FOG_SPIRIT, "For centuries, I have been forgotten, pushed to the shadows while the lehua receives all praise and offerings. I took what was never truly appreciated.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "You sense a deep loneliness in the spirit's voice.", 1.2)
        time.sleep(0.5)
        
        options = [
            "Offer to establish a new tradition honoring both the lehua and the night fog.",
            "Explain that balance requires all elements, including the night fog, and promise to teach others.",
            "Suggest that taking the stone will only bring more isolation, not the recognition it seeks."
        ]
        
        choice = self.get_user_choice(options, ChoiceCategory.NEGOTIATION)
        self.update_game_state(SceneType.SCENE_3_NEGOTIATE, choice)
        
        self.print_dialogue(CharacterType.NIGHT_FOG_SPIRIT, "Your words... they carry truth I have not heard in many generations.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "The spirit wavers, its misty form becoming less serpentine and more humanoid.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.NIGHT_FOG_SPIRIT, "I will return the seed stone, but you must keep your promise to remember the night fog in your stories and chants.", 0.8)
        time.sleep(0.5)
        
        return SceneType.FINAL_NEGOTIATE
        
    def final_scene_restore(self) -> SceneType:
        """Display Final Scene (Restore) and conclude the story."""
        self.clear_screen()
        self.print_scene_description("[Final Scene – Forest Restored, Gentle Rain Falls]")
        
        self.print_dialogue(CharacterType.HOST, "Your voice rises like wind through the leaves, and the cavern shimmers with golden light. The Night Fog Spirit shrieks once… and dissolves.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "The seed stone glows, roots itself into the earth, and sprouts a single, red lehua blossom. You have restored balance.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "Well done, Keola. You have honored the land, and the land will remember you.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "The winds sing again. The lehua stands tall. But remember—every choice carries mana, and with mana comes kuleana, responsibility.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "Until next time, guardian… A hui hou.", 1.2)
        
        self.game_state["game_over"] = True
        return SceneType.END
        
    def final_scene_shatter(self) -> SceneType:
        """Display Final Scene (Shatter) and conclude the story."""
        self.clear_screen()
        self.print_scene_description("[Final Scene – Shattered Stone, Fading Mist]")
        
        self.print_dialogue(CharacterType.HOST, "You bring the stone down hard against the cavern floor. It shatters with a sound like thunder, and a wave of energy knocks you backward.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "The Night Fog Spirit wails as it is pulled into the fragments, trapped forever in the broken pieces.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "The immediate danger is gone, but at what cost? The island will feel this loss for generations.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "As you exit the cavern, you notice the forest seems quieter. The lehua trees stand, but their blossoms are fewer. You have saved yourself and many others, but something sacred has been lost.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "Remember, guardian—power comes in many forms, and sometimes the hardest choice is not the wisest one.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "Until we meet again… A hui hou.", 1.2)
        
        self.game_state["game_over"] = True
        return SceneType.END
        
    def final_scene_negotiate(self) -> SceneType:
        """Display Final Scene (Negotiate) and conclude the story."""
        self.clear_screen()
        self.print_scene_description("[Final Scene – Harmony Restored, Dual Mist and Light]")
        
        self.print_dialogue(CharacterType.HOST, "The seed stone floats between you and the Night Fog Spirit, glowing with a light that now contains swirls of gentle mist.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "As it returns to the earth, both golden light and silver mist spread through the cavern and beyond, into the forest.", 1.2)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.AHI, "You have found a third path, Keola. Not just restoration, not just destruction, but transformation.", 0.8)
        time.sleep(0.5)
        
        self.print_dialogue(CharacterType.HOST, "In the days that follow, the island changes. The lehua trees bloom as before, but now at twilight they are embraced by a gentle, protective mist that the villagers come to cherish.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "You have taught an important lesson—that balance is not just about preserving what was, but finding harmony in what could be.", 1.2)
        time.sleep(0.5)
        self.print_dialogue(CharacterType.HOST, "Until our paths cross again, guardian of new traditions... A hui hou.", 1.2)
        
        self.game_state["game_over"] = True
        return SceneType.END
        
    def determine_ending_type(self) -> EndingType:
        """Determine the ending type based on player choices."""
        if SceneType.SCENE_3.value in self.game_state["choices_made"]:
            choice = self.game_state["choices_made"][SceneType.SCENE_3.value]
            if choice == 1:
                return EndingType.RESTORATION
            elif choice == 2:
                return EndingType.SACRIFICE
            else:
                return EndingType.HARMONY
        return EndingType.UNKNOWN
        
    def end_game(self) -> bool:
        """Display game ending and summary."""
        self.clear_screen()
        print("\n" + "*" * 80)
        self.slow_print("THE END", 0.5)
        print("*" * 80 + "\n")
        
        self.slow_print("Thank you for playing The Spirit of the Lehua Tree!", 1.5)
        time.sleep(0.5)
        
        # Display game summary
        print("\nYour Journey Summary:")
        print(f"- Locations visited: {len(self.game_state['visited_locations'])}")
        print(f"- Story choices made: {len(self.game_state['choices_made'])}")
        
        # Determine ending type
        ending = self.determine_ending_type()
        print(f"- Ending achieved: {ending.value}")
        
        # Ask if player wants to play again
        print("\nWould you like to play again?")
        options = ["Yes", "No"]
        choice = self.get_user_choice(options, ChoiceCategory.PLAY_AGAIN)
        
        return choice == 1
        
    def run_game(self):
        """Main game loop."""
        play_again = True
        
        while play_again:
            # Reset game state for new playthrough
            self.__init__()
            
            # Start with intro scene
            current_scene = SceneType.INTRO
            
            # Game loop
            while not self.game_state["game_over"]:
                # Call the appropriate scene method
                if current_scene == SceneType.INTRO:
                    current_scene = self.intro_scene()
                elif current_scene == SceneType.SCENE_1:
                    current_scene = self.scene_1()
                elif current_scene == SceneType.SCENE_1_MORE_INFO:
                    current_scene = self.scene_1_more_info()
                elif current_scene == SceneType.SCENE_2_RIDGE:
                    current_scene = self.scene_2_ridge()
                elif current_scene == SceneType.SCENE_2_LAVA:
                    current_scene = self.scene_2_lava()
                elif current_scene == SceneType.SCENE_3:
                    current_scene = self.scene_3()
                elif current_scene == SceneType.SCENE_3_NEGOTIATE:
                    current_scene = self.scene_3_negotiate()
                elif current_scene == SceneType.FINAL_RESTORE:
                    current_scene = self.final_scene_restore()
                elif current_scene == SceneType.FINAL_SHATTER:
                    current_scene = self.final_scene_shatter()
                elif current_scene == SceneType.FINAL_NEGOTIATE:
                    current_scene = self.final_scene_negotiate()
                elif current_scene == SceneType.END:
                    play_again = self.end_game()
                    break
                else:
                    print(f"\nError: Unknown scene {current_scene}")
                    play_again = False
                    break
                
            if current_scene != SceneType.END and not self.game_state["game_over"]:
                # If we broke out of the loop without reaching the end
                print("\nGame ended unexpectedly.")
                play_again = False

def main():
    """Main function to start the game."""
    game = TextAdventureGame()
    
    # Display welcome message
    print("\n" + "=" * 80)
    print("Welcome to THE SPIRIT OF THE LEHUA TREE".center(80))
    print("A Hawaiian Text Adventure".center(80))
    print("=" * 80 + "\n")
    
    print("In this adventure, you will play as Keola, a young guardian in training,")
    print("chosen to protect the sacred island of Moku Huna.")
    print("\nYour choices will shape the story and determine the fate of the island.")
    
    if not game.use_llm:
        print("\nNote: OpenAI API key not found. The game will use numbered choices.")
        print("To enable free-form text input, set the OPENAI_API_KEY environment variable.")
    else:
        print("\nYou can respond to choices using natural language instead of numbers.")
    
    print("\nPress Enter to begin your journey...")
    input()
    
    # Start the game
    game.run_game()
    
    print("\nThank you for playing! A hui hou (Until we meet again)!")

if __name__ == "__main__":
    main()
