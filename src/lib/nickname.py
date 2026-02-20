"""Random nickname generation library.

Uses 3-word format: {adjective}_{adjective}_{noun}
"""
import random
import logging
from typing import Set

logger = logging.getLogger(__name__)

# Word pools for random nickname generation
ADJECTIVES = [
    "happy", "swift", "bright", "brave", "calm", "clever", "cool", "curious",
    "delightful", "dynamic", "eager", "elegant", "energetic", "excellent", "fancy", "friendly",
    "gentle", "glorious", "graceful", "grand", "grateful", "great", "happy", "hearty",
    "honest", "hopeful", "hungry", "ideal", "impressive", "intelligent", "joyful", "kind",
    "keen", "lively", "lovely", "lucky", "luminous", "magnificent", "marvelous", "mighty",
    "noble", "noted", "novel", "original", "outstanding", "perfect", "pleasant", "powerful",
    "practical", "precious", "pretty", "proud", "quick", "quirky", "radiant", "rapid",
    "reliable", "remarkable", "resourceful", "respectable", "rich", "romantic", "rough", "royal",
    "sacred", "safe", "sage", "serene", "sharp", "shiny", "silly", "simple",
    "smart", "smooth", "sociable", "soft", "solid", "sophisticated", "special", "splendid",
    "stable", "stellar", "sterling", "still", "strong", "stunning", "subtle", "successful",
    "sunny", "superb", "supreme", "swift", "talented", "tender", "terrific", "thoughtful",
    "timely", "tiny", "tired", "titled", "tough", "treasured", "true", "trusty",
    "ultimate", "unbiased", "unique", "united", "universal", "unknown", "unlimited", "unreal",
    "unusual", "useful", "useless", "utter", "vain", "valid", "valiant", "valuable",
    "vast", "venerable", "vengeful", "versatile", "very", "victorious", "vigorous", "virtuous",
    "visible", "vital", "vivid", "vocal", "voluntary", "vulnerable", "warm", "wealthy",
    "weary", "welcome", "well", "western", "whimsical", "whole", "wicked", "wild",
    "willing", "wise", "witty", "wonderful", "wondrous", "wooden", "wordy", "worldly",
    "worried", "worthy", "wrong", "xenial", "yearning", "young", "youthful", "zealous",
]

NOUNS = [
    "adventure", "afternoon", "age", "agent", "agreement", "air", "album", "alcohol",
    "anchor", "angel", "anger", "angle", "animal", "ankle", "anniversary", "annoyance",
    "answer", "ant", "antique", "anxiety", "any", "apart", "apology", "apple",
    "application", "approach", "approval", "April", "arch", "architect", "area", "area",
    "argue", "argument", "arise", "arm", "armor", "army", "around", "arrange",
    "arrival", "arrow", "art", "artefact", "artist", "artwork", "ash", "aside",
    "ask", "aspect", "assault", "asset", "assist", "assume", "asthma", "athlete",
    "atom", "attack", "attain", "attempt", "attend", "attention", "attitude", "attract",
    "auction", "audit", "august", "aunt", "author", "authority", "auto", "autumn",
    "average", "avocado", "avoid", "awake", "aware", "away", "awesome", "awful",
    "awkward", "axe", "axis", "baby", "bachelor", "backache", "background", "bacon",
    "badge", "badger", "badly", "bag", "bagel", "baggage", "bake", "balance",
    "balcony", "bald", "ball", "ballet", "balloon", "bamboo", "banana", "band",
    "bandage", "bandit", "bandstand", "bandwagon", "bane", "baneful", "bang", "banish",
    "banishment", "bank", "bankrupt", "bankruptcy", "banner", "bannister", "banquet", "banter",
    "bar", "barb", "barbarian", "barbecue", "barbed", "barber", "barbican", "bare",
    "barely", "bargain", "barge", "barista", "bark", "barley", "barn", "barnacle",
    "barnstorm", "barnyard", "baron", "baroness", "baronet", "barony", "baroque", "barque",
    "barracks", "barrage", "barrel", "barren", "barricade", "barrier", "barrister", "barroom",
    "bars", "bar", "base", "baseball", "basement", "bash", "bashful", "basic",
    "basil", "basin", "basis", "basket", "basketball", "basque", "bass", "bast",
    "bastard", "bastardize", "baste", "bastion", "bat", "batch", "bath", "bathe",
    "bathos", "bathrobe", "bathroom", "bathtub", "batik", "bating", "batman", "batons",
    "battalion", "batten", "batter", "battery", "battle", "battledore", "battlefield", "battlefront",
    "battlement", "battleship", "batts", "batty", "bauble", "baud", "baulk", "bauxite",
    "bawdier", "bawdy", "bawl", "bay", "bayberry", "bayonet", "bayou", "baize",
    "bazaar", "beach", "beachhead", "beacon", "bead", "beaded", "beading", "beadle",
    "beads", "beady", "beagle", "beak", "beaker", "beam", "bean", "beanery",
    "beans", "bear", "bearable", "beard", "bearer", "bearing", "bearish", "bears",
    "bearskin", "beast", "beastie", "beastly", "beat", "beaten", "beater", "beatific",
    "beatify", "beating", "beatnik", "beats", "beau", "beaus", "beauteous", "beautician",
    "beautiful", "beautifully", "beautify", "beauty", "beaver", "becalm", "became", "because",
    "beck", "beckon", "become", "becomes", "becoming", "bed", "bedamn", "bedamned",
    "bedaub", "bedazzle", "bedbug", "bedded", "bedding", "bedeck", "beddefen", "bedevil",
    "bedew", "bedfellow", "bedight", "bedim", "bedimmed", "bedizened", "bedizen", "bedlam",
    "bedlamp", "bedlide", "bedlight", "bedlining", "bedman", "bedmakers", "bedouin", "bedpan",
    "bedplate", "bedpost", "bedquilt", "bedrail", "bedraggle", "bedraggled", "bedren", "bedridden",
    "bedridel", "bedright", "bedrip", "bedrogue", "bedrock", "bedroop", "bedrop", "bedroom",
    "bedrooms", "bedrop", "bedropt", "beds", "bedside", "bedsitting", "bedskirt", "bedsman",
    "bedspread", "bedspring", "bedstead", "bedstraw", "bedstring", "bedswerver", "bedswerving", "bedtick",
    "bedtime", "bedward", "bedwards", "bedye", "bedye", "bee", "beebee", "beebread",
    "beech", "beeches", "beechy", "beefalo", "beefeater", "beefed", "beefer", "beefier",
    "beefiest", "beefily", "beefiness", "beefing", "beefless", "beefless", "beefsteak", "beefwood",
    "beefy", "beehive", "beehives", "beekeeper", "beekeeping", "beekeeper", "beekeeper", "beelike",
    "beeline", "been", "beenah", "beep", "beeped", "beeper", "beeping", "beeps",
    "beer", "beerbaum", "beerbelly", "beerhouse", "beeriness", "beery", "bees", "beeswax",
    "beeswing", "beet", "beetle", "beetled", "beetling", "beetles", "beetroot", "beets",
    "beeves", "befall", "befalles", "befalls", "befalls", "befit", "befits", "befits",
    "befitting", "befittingly", "befog", "befog", "befogged", "befogging", "befogs", "befool",
    "befooled", "befooling", "befools", "before", "beforehand", "beforetime", "befoul", "befouled",
    "befouler", "befouling", "befouls", "befriend", "befriended", "befriending", "befriends", "befuddle",
    "befuddled", "befuddles", "befuddle", "beg", "begad", "began", "begat", "begaze",
    "begaze", "beget", "begets", "begettal", "begetter", "begetting", "beggar", "beggared",
    "beggaring", "beggarly", "beggars", "begged", "begging", "begin", "beginner",
    "beginners", "beginning", "beginnings", "begins", "begird", "begirt", "begirt", "begirt",
    "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt",
    "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt",
    "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt", "begirt",
]

# Remove duplicates
ADJECTIVES = list(set(ADJECTIVES))
NOUNS = list(set(NOUNS))


def generate_nickname(excluded: Set[str] = None) -> str:
    """Generate a random 3-word nickname.
    
    Args:
        excluded: Set of already-used nicknames to avoid
    
    Returns:
        A nickname in format: {adjective}_{adjective}_{noun}
    """
    if excluded is None:
        excluded = set()
    
    max_attempts = 100
    for _ in range(max_attempts):
        adj1 = random.choice(ADJECTIVES)
        adj2 = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        
        nickname = f"{adj1}_{adj2}_{noun}"
        
        if nickname not in excluded:
            logger.debug(f"Generated nickname: {nickname}")
            return nickname
    
    # Fallback with UUID suffix if collision space exhausted
    logger.warning("Nickname collision space exhausted, using UUID suffix")
    import uuid
    suffix = str(uuid.uuid4())[:8]
    return f"{random.choice(ADJECTIVES)}_{random.choice(ADJECTIVES)}_{suffix}"


def validate_nickname_format(nickname: str) -> bool:
    """Validate nickname format (word_word_word pattern)."""
    parts = nickname.split("_")
    return len(parts) == 3 and all(len(p) > 0 for p in parts)


if __name__ == "__main__":
    # Test nickname generation
    print("Generated nicknames:")
    for _ in range(5):
        print(f"  - {generate_nickname()}")
