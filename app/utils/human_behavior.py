"""Human behavior enhancement - Make responses more natural with typos, errors, and hesitations."""
import random
import re
from typing import List, Tuple


class HumanBehavior:
    """Add human-like imperfections to agent responses."""
    
    # Common typos patterns
    TYPO_PATTERNS = [
        # Swap adjacent letters
        (r"the", ["teh", "hte"]),
        (r"you", ["yuo", "oyu"]),
        (r"what", ["waht", "wha"]),
        (r"that", ["taht", "thta"]),
        (r"this", ["thsi", "tihs"]),
        (r"wait", ["wiat", "wiat"]),
        (r"just", ["jsut", "jstu"]),
        (r"know", ["konw", "knwo"]),
        (r"your", ["yoru", "yuor"]),
        (r"with", ["wiht", "wtih"]),
    ]
    
    # Missing letters
    MISSING_LETTERS = [
        (r"please", ["plase", "pls", "plz"]),
        (r"because", ["becoz", "bcoz", "bcz"]),
        (r"actually", ["actuly", "akchhly"]),
        (r"really", ["relly", "realy"]),
        (r"understand", ["undrstand", "understnd"]),
        (r"important", ["importnt", "imptnt"]),
    ]
    
    # Hinglish shortcuts
    HINGLISH_SHORTCUTS = [
        (r" you ", [" u "]),
        (r" your ", [" ur "]),
        (r" are ", [" r "]),
        (r" okay ", [" ok ", " k "]),
        (r" thanks ", [" thnx ", " thx "]),
        (r" what ", [" wht ", " wat "]),
        (r" why ", [" y "]),
    ]
    
    # Emotional markers
    EMOTIONAL_MARKERS = {
        "excited": ["!", "!!", "!!!", "Woah!", "Hayy!"],
        "confused": ["?", "??", "Huh?", "Matlab?"],
        "worried": ["...", "Oh no!", "Arre baap re!"],
        "hesitant": ["Umm", "Uhh", "Hmm", "Well"],
    }
    
    # Hesitation phrases
    HESITATIONS = [
        "wait wait",
        "one sec",
        "just a minute",
        "hold on",
        "let me think",
        "umm",
        "actually"
    ]
    
    def __init__(self, typo_probability: float = 0.15, shortcut_probability: float = 0.20):
        """
        Initialize human behavior enhancer.
        
        Args:
            typo_probability: Chance of introducing a typo (0.0-1.0)
            shortcut_probability: Chance of using shortcuts like 'u' instead of 'you'
        """
        self.typo_prob = typo_probability
        self.shortcut_prob = shortcut_probability
    
    def add_typos(self, text: str) -> str:
        """Add realistic typos to text."""
        if random.random() > self.typo_prob:
            return text  # No typo this time
        
        # Combine all patterns
        all_patterns = self.TYPO_PATTERNS + self.MISSING_LETTERS
        
        # Randomly pick one pattern to apply
        if all_patterns:
            pattern, replacements = random.choice(all_patterns)
            if re.search(pattern, text, re.IGNORECASE):
                replacement = random.choice(replacements)
                # Replace first occurrence only
                text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
        
        return text
    
    def add_shortcuts(self, text: str) -> str:
        """Add Hinglish shortcuts like 'u' instead of 'you'."""
        if random.random() > self.shortcut_prob:
            return text
        
        # Apply one random shortcut
        if self.HINGLISH_SHORTCUTS:
            pattern, replacements = random.choice(self.HINGLISH_SHORTCUTS)
            if re.search(pattern, text, re.IGNORECASE):
                replacement = random.choice(replacements)
                text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
        
        return text
    
    def add_repetitions(self, text: str) -> str:
        """Add word repetitions like 'wait wait' or 'achha achha'."""
        if random.random() > 0.10:  # 10% chance
            return text
        
        # Common repeatable words
        repeatable_words = ["wait", "okay", "achha", "haan", "no", "yes", "what"]
        
        for word in repeatable_words:
            pattern = r'\b' + word + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Repeat it 2x
                text = re.sub(pattern, f"{word} {word}", text, count=1, flags=re.IGNORECASE)
                break
        
        return text
    
    def add_hesitation(self, text: str) -> str:
        """Add hesitation markers at the beginning."""
        if random.random() > 0.15:  # 15% chance
            return text
        
        hesitation = random.choice(self.HESITATIONS)
        
        # Add at beginning with comma
        if not text.startswith(("Wait", "Umm", "Hmm", "Just", "Hold")):
            text = f"{hesitation.capitalize()}, {text}"
        
        return text
    
    def remove_some_punctuation(self, text: str) -> str:
        """Remove some punctuation to seem more casual."""
        if random.random() > 0.20:  # 20% chance
            return text
        
        # Remove ending period if present
        if text.endswith('.'):
            text = text[:-1]
        
        # Remove some commas
        if ',' in text and random.random() > 0.5:
            text = text.replace(',', '', 1)
        
        return text
    
    def add_emotional_marker(self, text: str, emotion: str = None) -> str:
        """Add emotional markers like '!!' or '??'."""
        if emotion is None:
            # Detect emotion from text
            if any(word in text.lower() for word in ["wow", "great", "awesome", "nice"]):
                emotion = "excited"
            elif "?" in text:
                emotion = "confused"
            elif any(word in text.lower() for word in ["problem", "issue", "wrong", "blocked"]):
                emotion = "worried"
            else:
                emotion = "hesitant"
        
        if emotion in self.EMOTIONAL_MARKERS:
            marker = random.choice(self.EMOTIONAL_MARKERS[emotion])
            
            # Add marker if not already very expressive
            if text.count('!') < 2 and text.count('?') < 2:
                if text.endswith(('.', '!', '?')):
                    text = text[:-1]
                text = f"{text} {marker}"
        
        return text
    
    def enhance(self, text: str, persona: str = "uncle", turn_count: int = 0) -> str:
        """
        Apply all human behavior enhancements.
        
        Args:
            text: Original text
            persona: Agent persona (affects style)
            turn_count: Current turn number (more errors as conversation progresses)
        
        Returns:
            Enhanced text with human-like imperfections
        """
        # Increase typo probability as conversation gets longer (getting tired)
        self.typo_prob = min(0.15 + (turn_count * 0.01), 0.30)
        
        # Apply enhancements in sequence
        enhanced = text
        
        # Student and younger personas use more shortcuts
        if persona in ["student", "techsavvy"]:
            enhanced = self.add_shortcuts(enhanced)
        
        # All personas get typos
        enhanced = self.add_typos(enhanced)
        
        # Aunty and Uncle repeat words more
        if persona in ["aunty", "uncle"]:
            enhanced = self.add_repetitions(enhanced)
        
        # Add hesitation occasionally
        enhanced = self.add_hesitation(enhanced)
        
        # Make more casual
        enhanced = self.remove_some_punctuation(enhanced)
        
        # Add emotional markers (less for techsavvy)
        if persona != "techsavvy":
            enhanced = self.add_emotional_marker(enhanced)
        
        return enhanced


# Global instance
human_behavior = HumanBehavior()


# Convenience functions
def make_human(text: str, persona: str = "uncle", turn_count: int = 0) -> str:
    """
    Quick function to make text more human-like.
    
    Usage:
        response = "Please wait while I check"
        response = make_human(response, persona="aunty", turn_count=5)
        # Result: "Umm, pleae wiat while I check!"
    """
    return human_behavior.enhance(text, persona, turn_count)
