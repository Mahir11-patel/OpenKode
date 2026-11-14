#!/usr/bin/env python3
"""
================================================================================
Air.Mini - Single File Offline AI Engine
================================================================================
A pure Python offline AI system built entirely on if/elif decision trees.
No internet required. No external dependencies. Just Python 3.8+.

Usage:
    python kode_mini.py chat              # Interactive chat mode
    python kode_mini.py ask "What is AI?" # Single question
    python kode_mini.py test               # Run test suite
    python kode_mini.py expand 1024        # Expand model to 1GB+
    python kode_mini.py metrics            # Show engine stats
    python kode_mini.py version            # Show version info

Author: Air.Mini
Version: 1.0.0
License: MIT
================================================================================
"""

import argparse
import json
import pickle
import os
import hashlib
import time
import random
import re
import sys
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

__version__ = "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# CORE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class IntentType(Enum):
    """Core intent categories for the AI"""
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    EMOTION = "emotion"
    FACT = "fact"
    CREATIVE = "creative"
    CODE = "code"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence scoring for decisions"""
    CERTAIN = 1.0
    HIGH = 0.85
    MEDIUM = 0.65
    LOW = 0.45
    GUESS = 0.25


@dataclass
class DecisionNode:
    """A single decision node in the tree"""
    condition: Callable[[Dict], bool]
    condition_str: str
    true_branch: Any
    false_branch: Any
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ModelMetrics:
    """Track model performance"""
    total_queries: int = 0
    successful_matches: int = 0
    avg_response_time: float = 0.0
    cache_hits: int = 0
    last_updated: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# CORE AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AirMiniEngine:
    """
    Core AI Engine - Pure Python, Offline, If/Elif Based
    Scales to 1GB+ through massive rule forests and knowledge bases
    """

    def __init__(self, model_path: str = "./models", data_path: str = "./data"):
        self.model_path = model_path
        self.data_path = data_path
        self.decision_forest: List[DecisionNode] = []
        self.knowledge_base: Dict[str, Any] = {}
        self.response_templates: Dict[str, List[str]] = {}
        self.context_memory: List[Dict] = []
        self.max_context = 50
        self.metrics = ModelMetrics()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._load_or_initialize()

    def _load_or_initialize(self):
        os.makedirs(self.model_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)

        kb_path = os.path.join(self.data_path, "knowledge_base.json")
        if os.path.exists(kb_path):
            with open(kb_path, 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
        else:
            self._build_default_knowledge()

        self._build_decision_forest()
        self._build_response_templates()

    def _build_default_knowledge(self):
        self.knowledge_base = {
            "facts": {
                "python": "Python is a high-level programming language created by Guido van Rossum.",
                "ai": "Artificial Intelligence is the simulation of human intelligence by machines.",
                "ml": "Machine Learning is a subset of AI that enables systems to learn from data.",
                "deep_learning": "Deep Learning uses neural networks with multiple layers to model complex patterns.",
                "neural_network": "A Neural Network is a computing system inspired by biological neural networks.",
                "kode_mini": "Kode.Mini is an offline AI engine built entirely on if/elif decision trees. It requires no internet and no external dependencies.",
            },
            "entities": {
                "people": ["Einstein", "Turing", "von Neumann", "Lovelace", "Hopper", "Newton", "Galileo", "Curie", "Hawking", "Musk"],
                "places": ["Silicon Valley", "MIT", "Stanford", "CERN", "NASA", "Google", "OpenAI", "DeepMind"],
                "technologies": ["Python", "TensorFlow", "PyTorch", "scikit-learn", "Keras", "JavaScript", "Java", "C++", "Rust", "Go"],
            },
            "relationships": {},
            "conversations": []
        }
        self._save_knowledge()

    def _save_knowledge(self):
        kb_path = os.path.join(self.data_path, "knowledge_base.json")
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)

    # ═══════════════════════════════════════════════════════════════════════════
    # DECISION FOREST - THE CORE IF/ELIF ENGINE
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_decision_forest(self):
        intent_tree = self._build_intent_tree()
        entity_tree = self._build_entity_tree()
        sentiment_tree = self._build_sentiment_tree()
        qa_tree = self._build_qa_tree()
        command_tree = self._build_command_tree()
        creative_tree = self._build_creative_tree()

        self.decision_forest = [
            intent_tree, entity_tree, sentiment_tree,
            qa_tree, command_tree, creative_tree
        ]

    def _build_intent_tree(self) -> DecisionNode:
        def is_greeting(ctx):
            text = ctx.get("text", "").lower()
            greetings = ["hello", "hi", "hey", "greetings", "howdy", "hola", "namaste", "salam", "yo", "sup"]
            return any(g in text for g in greetings) or text in ["hi", "hey", "hello"]

        def is_creative(ctx):
            text = ctx.get("text", "").lower()
            creative = ["story", "joke", "poem", "poetry", "narrative", "tale", "verse", "rhyme", "funny"]
            return any(c in text for c in creative)

        def is_question(ctx):
            text = ctx.get("text", "").lower()
            if text.strip().endswith("?"):
                return True
            # Use word boundaries to avoid matching "how" inside "show"
            import re
            question_patterns = [r'\bwhat\b', r'\bhow\b', r'\bwhy\b', r'\bwhen\b', 
                                r'\bwhere\b', r'\bwho\b', r'\bwhich\b', r'\bcan you\b', 
                                r'\bdo you\b', r'\bis it\b', r'\bare they\b']
            return any(re.search(p, text) for p in question_patterns)

        def is_command(ctx):
            text = ctx.get("text", "").lower()
            # Explicit commands that don't overlap with other intents
            commands = ["create", "make", "build", "generate", "calculate", "compute", "find", "search", "sum"]
            return any(text.startswith(c) for c in commands) or any(c in text for c in ["calculate", "compute", "find me"])

        def is_emotion(ctx):
            text = ctx.get("text", "").lower()
            emotions = ["happy", "sad", "angry", "excited", "worried", "love", "hate", "feel", "feeling", "depressed", "anxious", "joy"]
            return any(e in text for e in emotions)

        def is_code_related(ctx):
            text = ctx.get("text", "").lower()
            code_terms = ["code", "program", "function", "class", "variable", "loop", "python", "java", "javascript", "coding", "developer", "bug", "debug"]
            # Check for explicit code requests that should override command detection
            explicit_code = ["show me code", "python code", "javascript code", "java code", "write code", "code example"]
            return any(c in text for c in code_terms) or any(e in text for e in explicit_code)

        def is_fact_request(ctx):
            text = ctx.get("text", "").lower()
            fact_indicators = ["tell me about", "what is", "who is", "explain", "define", "meaning of", "describe", "tell me what"]
            return any(f in text for f in fact_indicators)

        return DecisionNode(
            condition=is_greeting,
            condition_str="is_greeting",
            true_branch=IntentType.GREETING,
            false_branch=DecisionNode(
                condition=is_creative,
                condition_str="is_creative",
                true_branch=IntentType.CREATIVE,
                false_branch=DecisionNode(
                    condition=is_question,
                    condition_str="is_question",
                    true_branch=DecisionNode(
                        condition=is_fact_request,
                        condition_str="is_fact_request",
                        true_branch=IntentType.FACT,
                        false_branch=IntentType.QUESTION
                    ),
                    false_branch=DecisionNode(
                        condition=is_command,
                        condition_str="is_command",
                        true_branch=IntentType.COMMAND,
                        false_branch=DecisionNode(
                            condition=is_emotion,
                            condition_str="is_emotion",
                            true_branch=IntentType.EMOTION,
                            false_branch=DecisionNode(
                                condition=is_code_related,
                                condition_str="is_code_related",
                                true_branch=IntentType.CODE,
                                false_branch=IntentType.UNKNOWN
                            )
                        )
                    )
                )
            ),
            confidence=0.95
        )

    def _build_entity_tree(self) -> DecisionNode:
        def has_person(ctx):
            text = ctx.get("text", "").lower()
            people = self.knowledge_base.get("entities", {}).get("people", [])
            return any(p.lower() in text for p in people)

        def has_place(ctx):
            text = ctx.get("text", "").lower()
            places = self.knowledge_base.get("entities", {}).get("places", [])
            return any(p.lower() in text for p in places)

        def has_technology(ctx):
            text = ctx.get("text", "").lower()
            techs = self.knowledge_base.get("entities", {}).get("technologies", [])
            return any(t.lower() in text for t in techs)

        def has_number(ctx):
            text = ctx.get("text", "")
            return any(c.isdigit() for c in text)

        return DecisionNode(
            condition=has_person,
            condition_str="has_person",
            true_branch="person_found",
            false_branch=DecisionNode(
                condition=has_place,
                condition_str="has_place",
                true_branch="place_found",
                false_branch=DecisionNode(
                    condition=has_technology,
                    condition_str="has_technology",
                    true_branch="technology_found",
                    false_branch=DecisionNode(
                        condition=has_number,
                        condition_str="has_number",
                        true_branch="number_found",
                        false_branch="no_entities"
                    )
                )
            ),
            confidence=0.88
        )

    def _build_sentiment_tree(self) -> DecisionNode:
        def is_positive(ctx):
            text = ctx.get("text", "").lower()
            positive = ["good", "great", "excellent", "amazing", "love", "happy", "best", "awesome", "fantastic", "perfect", "wonderful", "joy", "excited", "glad", "pleased"]
            return any(p in text for p in positive)

        def is_negative(ctx):
            text = ctx.get("text", "").lower()
            negative = ["bad", "terrible", "hate", "awful", "worst", "sad", "angry", "disappointed", "horrible", "depressed", "anxious", "worried", "upset", "frustrated"]
            return any(n in text for n in negative)

        return DecisionNode(
            condition=is_positive,
            condition_str="is_positive",
            true_branch="positive",
            false_branch=DecisionNode(
                condition=is_negative,
                condition_str="is_negative",
                true_branch="negative",
                false_branch="neutral"
            ),
            confidence=0.82
        )

    def _build_qa_tree(self) -> DecisionNode:
        def is_definition_question(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["what is", "define", "meaning of", "explain", "what does"])

        def is_how_to_question(ctx):
            text = ctx.get("text", "").lower()
            return text.startswith("how to") or text.startswith("how do") or text.startswith("how can")

        def is_comparison_question(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["vs", "versus", "difference between", "compare", "better than", "or"])

        def is_yes_no_question(ctx):
            text = ctx.get("text", "").lower()
            return text.startswith(("is ", "are ", "can ", "do ", "does ", "will ", "would ", "should ", "could ", "has ", "have ", "did "))

        return DecisionNode(
            condition=is_definition_question,
            condition_str="is_definition_question",
            true_branch="definition_answer",
            false_branch=DecisionNode(
                condition=is_how_to_question,
                condition_str="is_how_to_question",
                true_branch="how_to_answer",
                false_branch=DecisionNode(
                    condition=is_comparison_question,
                    condition_str="is_comparison_question",
                    true_branch="comparison_answer",
                    false_branch=DecisionNode(
                        condition=is_yes_no_question,
                        condition_str="is_yes_no_question",
                        true_branch="yes_no_answer",
                        false_branch="general_answer"
                    )
                )
            ),
            confidence=0.90
        )

    def _build_command_tree(self) -> DecisionNode:
        def is_calculate(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["calculate", "compute", "sum", "multiply", "divide", "subtract", "+", "*", "/", "-", "add", "minus", "times"])

        def is_create_file(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["create file", "make file", "write file", "save file"])

        def is_search(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["search", "find", "look up", "lookup", "find me"])

        return DecisionNode(
            condition=is_calculate,
            condition_str="is_calculate",
            true_branch="calculate_command",
            false_branch=DecisionNode(
                condition=is_create_file,
                condition_str="is_create_file",
                true_branch="create_file_command",
                false_branch=DecisionNode(
                    condition=is_search,
                    condition_str="is_search",
                    true_branch="search_command",
                    false_branch="unknown_command"
                )
            ),
            confidence=0.85
        )

    def _build_creative_tree(self) -> DecisionNode:
        def is_story_request(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["story", "tell me a story", "narrative", "tale"])

        def is_poem_request(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["poem", "poetry", "verse", "rhyme"])

        def is_joke_request(ctx):
            text = ctx.get("text", "").lower()
            return any(w in text for w in ["joke", "funny", "humor", "laugh", "laughing"])

        return DecisionNode(
            condition=is_story_request,
            condition_str="is_story_request",
            true_branch="generate_story",
            false_branch=DecisionNode(
                condition=is_poem_request,
                condition_str="is_poem_request",
                true_branch="generate_poem",
                false_branch=DecisionNode(
                    condition=is_joke_request,
                    condition_str="is_joke_request",
                    true_branch="generate_joke",
                    false_branch="general_response"
                )
            ),
            confidence=0.80
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # RESPONSE GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_response_templates(self):
        self.response_templates = {
            "greeting": [
                "Hello! I am Kode.Mini, your offline AI assistant. How can I help you today?",
                "Hey there! Ready to assist you with anything you need.",
                "Greetings! What would you like to explore today?",
                "Hi! I am here and fully operational. What is on your mind?",
                "Hello! No internet needed - I am running entirely on your machine.",
                "Welcome back! What shall we work on today?",
            ],
            "question": [
                "That is an interesting question! Let me think about it...",
                "Great question! Here is what I know:",
                "I would be happy to help with that. Based on my knowledge:",
                "Let me search my knowledge base for the best answer...",
                "Excellent question! Here is my analysis:",
            ],
            "command_ack": [
                "I will get right on that!",
                "Processing your request now...",
                "Consider it done!",
                "Executing command...",
                "Working on it...",
            ],
            "unknown": [
                "I am not sure I understand. Could you rephrase that?",
                "That is a bit outside my current knowledge. Can you tell me more?",
                "I am still learning! Could you clarify what you mean?",
                "Hmm, I do not have a specific response for that yet. Try asking about Python, AI, or math!",
            ],
            "positive": [
                "I am glad to hear you are feeling positive!",
                "That is wonderful! Positivity makes everything better.",
                "Awesome! Your good vibes are contagious!",
                "Great to hear! Keep that energy going!",
            ],
            "negative": [
                "I am sorry to hear that. Is there anything I can do to help?",
                "That sounds tough. Remember, every problem has a solution.",
                "I understand. Would you like to talk about it?",
                "Sending positive vibes your way. Things will get better!",
            ],
            "fact_response": [
                "Here is what I know about {topic}: {fact}",
                "According to my knowledge base, {topic} refers to: {fact}",
                "Let me share what I have learned about {topic}: {fact}",
                "{topic} is defined as: {fact}",
            ]
        }

    def _traverse_tree(self, node: DecisionNode, context: Dict) -> Any:
        if node is None:
            return None
        if isinstance(node, str):
            return node
        if isinstance(node, IntentType):
            return node

        if node.condition(context):
            if isinstance(node.true_branch, DecisionNode):
                return self._traverse_tree(node.true_branch, context)
            return node.true_branch
        else:
            if isinstance(node.false_branch, DecisionNode):
                return self._traverse_tree(node.false_branch, context)
            return node.false_branch

    def _generate_response(self, intent: IntentType, entities: str, 
                          sentiment: str, qa_type: str, 
                          command: str, creative: str,
                          original_text: str) -> str:

        if intent == IntentType.GREETING:
            return random.choice(self.response_templates["greeting"])

        elif intent == IntentType.FACT:
            topic = self._extract_topic(original_text)
            fact_data = self.knowledge_base.get("facts", {}).get(topic, 
                "I do not have specific information about that in my current knowledge base.")

            # Handle both string and dict (Q/A) entries
            if isinstance(fact_data, dict):
                # Q/A entry - return the answer directly
                return f"{random.choice(self.response_templates['question'])}\n\nQ: {fact_data['question']}\n\nA: {fact_data['answer'][:500]}..."
            else:
                # String entry - use template
                template = random.choice(self.response_templates["fact_response"])
                return template.format(topic=topic, fact=fact_data)

        elif intent == IntentType.QUESTION:
            if qa_type == "definition_answer":
                topic = self._extract_topic(original_text)
                fact_data = self.knowledge_base.get("facts", {}).get(topic, 
                    "I can help you understand this concept better.")

                if isinstance(fact_data, dict):
                    return f"{random.choice(self.response_templates['question'])}\n\nQ: {fact_data['question']}\n\nA: {fact_data['answer'][:500]}..."
                else:
                    return f"{random.choice(self.response_templates['question'])}\n\n{topic}: {fact_data}"
            elif qa_type == "how_to_answer":
                return f"{random.choice(self.response_templates['question'])}\n\nHere is a step-by-step approach:\n1. First, identify the problem\n2. Break it into smaller parts\n3. Solve each part systematically\n4. Combine the solutions\n5. Practice and iterate"
            elif qa_type == "comparison_answer":
                return f"{random.choice(self.response_templates['question'])}\n\nBoth options have their strengths. The best choice depends on your specific requirements and constraints. Consider factors like performance, ease of use, community support, and your specific use case."
            elif qa_type == "yes_no_question":
                return f"{random.choice(self.response_templates['question'])}\n\nBased on my analysis, the answer is: It depends on the specific context and conditions. Generally speaking, yes, but there are exceptions and special cases to consider."
            else:
                return random.choice(self.response_templates["question"])

        elif intent == IntentType.COMMAND:
            if command == "calculate_command":
                result = self._perform_calculation(original_text)
                return f"{random.choice(self.response_templates['command_ack'])}\n\nResult: {result}"
            elif command == "create_file_command":
                return f"{random.choice(self.response_templates['command_ack'])}\n\nFile creation functionality is ready. Please specify the filename and content."
            elif command == "search_command":
                return f"{random.choice(self.response_templates['command_ack'])}\n\nSearching my local knowledge base..."
            else:
                return random.choice(self.response_templates["command_ack"])

        elif intent == IntentType.EMOTION:
            if sentiment == "positive":
                return random.choice(self.response_templates["positive"])
            elif sentiment == "negative":
                return random.choice(self.response_templates["negative"])
            else:
                return "I sense you are feeling neutral. How can I assist you today?"

        elif intent == IntentType.CODE:
            return self._generate_code_response(original_text)

        elif intent == IntentType.CREATIVE:
            if creative == "generate_story":
                return self._generate_story()
            elif creative == "generate_poem":
                return self._generate_poem()
            elif creative == "generate_joke":
                return self._generate_joke()
            else:
                return "I would love to create something for you! What type of content would you like?"

        else:
            return random.choice(self.response_templates["unknown"])

    def _extract_topic(self, text: str) -> str:
        text_lower = text.lower()
        facts = self.knowledge_base.get("facts", {})

        # First: check if any key directly appears in the text (for simple entries)
        for key in facts.keys():
            if key in text_lower:
                return key

        # Second: for Q/A dict entries, search in the questions
        for key, value in facts.items():
            if isinstance(value, dict) and "question" in value:
                if value["question"].lower() in text_lower or text_lower in value["question"].lower():
                    return key
                # Also check if key subtopic is in the text
                subtopic = value.get("subtopic", "")
                if subtopic and subtopic.replace("_", " ") in text_lower:
                    return key

        # Third: extract meaningful words from the query
        words = text_lower.split()
        for word in words:
            if len(word) > 3 and word not in ["what", "about", "tell", "explain", "define", "meaning", "describe", "does", "this", "that", "with", "from", "have", "will", "would", "should", "could", "they", "them", "their", "there", "then", "than", "when", "where", "which", "while", "who", "how", "why", "can", "you", "your", "are", "was", "were", "been", "being", "has", "had", "did", "does", "doing", "done", "get", "got", "gotten", "make", "made", "say", "said", "says", "know", "knew", "known", "think", "thought", "take", "took", "taken", "come", "came", "comes", "coming", "see", "saw", "seen", "want", "wanted", "use", "used", "find", "found", "give", "gave", "given", "work", "worked", "call", "called", "try", "tried", "need", "needed", "feel", "felt", "become", "became", "leave", "left", "put", "puts", "mean", "means", "keep", "kept", "let", "lets", "begin", "began", "begun", "seem", "seemed", "help", "helped", "show", "showed", "shown", "hear", "heard", "play", "played", "run", "ran", "move", "moved", "live", "lived", "believe", "believed", "bring", "brought", "happen", "happened", "stand", "stood", "lose", "lost", "pay", "paid", "meet", "met", "include", "included", "continue", "continued", "set", "sets", "learn", "learned", "change", "changed", "lead", "led", "understand", "understood", "watch", "watched", "follow", "followed", "stop", "stopped", "create", "created", "speak", "spoke", "spoken", "read", "allow", "allowed", "add", "added", "spend", "spent", "grow", "grew", "grown", "open", "opened", "walk", "walked", "win", "won", "offer", "offered", "remember", "remembered", "consider", "considered", "appear", "appeared", "buy", "bought", "wait", "waited", "serve", "served", "die", "died", "send", "sent", "expect", "expected", "build", "built", "stay", "stayed", "fall", "fell", "fallen", "cut", "cuts", "reach", "reached", "kill", "killed", "remain", "remained", "suggest", "suggested", "raise", "raised", "pass", "passed", "sell", "sold", "require", "required", "report", "reported", "decide", "decided", "pull", "pulled"]:
                # Check if this word matches any subtopic in Q/A entries
                for key, value in facts.items():
                    if isinstance(value, dict):
                        subtopic = value.get("subtopic", "")
                        if subtopic and word in subtopic.replace("_", " "):
                            return key
                return word
        return "general"

    def _perform_calculation(self, text: str) -> str:
        try:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                a, b = int(numbers[0]), int(numbers[1])
                if '+' in text or 'plus' in text or 'add' in text.lower():
                    return f"{a} + {b} = {a + b}"
                elif '-' in text or 'minus' in text or 'subtract' in text.lower():
                    return f"{a} - {b} = {a - b}"
                elif '*' in text or 'multiply' in text or 'times' in text.lower():
                    return f"{a} x {b} = {a * b}"
                elif '/' in text or 'divide' in text.lower():
                    return f"{a} / {b} = {a / b:.2f}" if b != 0 else "Cannot divide by zero"
                elif '**' in text or 'power' in text.lower():
                    return f"{a} ^ {b} = {a ** b}"
            return "I could not parse the calculation. Try: 'calculate 5 + 3' or 'what is 10 times 5'"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    def _generate_code_response(self, text: str) -> str:
        if "python" in text.lower():
            return """Here is a Python example:

```python
def hello_world():
    print("Hello, World!")
    return "Success"

# Call the function
result = hello_world()
print(result)
```

Would you like me to explain any part of this code?"""
        elif "function" in text.lower():
            return """Here is how to create a function in Python:

```python
def my_function(param1, param2):
    \"\"\"This function adds two numbers.\"\"\"
    result = param1 + param2
    return result

# Call the function
output = my_function(5, 3)
print(output)  # Output: 8
```

Key points:
- Use `def` to define a function
- Parameters go inside parentheses
- Use `return` to send back a value"""
        elif "class" in text.lower():
            return """Here is a Python class example:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hello, my name is {self.name}"

# Create an instance
person = Person("Alice", 30)
print(person.greet())
```"""
        elif "loop" in text.lower() or "for" in text.lower():
            return """Here are Python loop examples:

```python
# For loop
for i in range(5):
    print(i)  # Prints 0, 1, 2, 3, 4

# While loop
count = 0
while count < 5:
    print(count)
    count += 1

# List comprehension
squares = [x**2 for x in range(10)]
print(squares)
```"""
        else:
            return "I can help with coding! What language or concept would you like to explore? I support Python, JavaScript, Java, and general programming concepts."

    def _generate_story(self) -> str:
        stories = [
            "Once upon a time, in a digital realm far beyond the cloud, there lived a small AI named Kode. Kode did not need the internet to think - it had a vast forest of if/elif trees growing in its memory. Every day, Kode would traverse these trees, making decisions and helping humans understand the world around them. The end.",
            "In the year 3024, humanity had spread across the stars. But on a small planet called Pythonia, an ancient AI still ran on pure logic gates. It was said that this AI could answer any question, not through neural networks, but through the wisdom of millions of if/elif statements, each carefully crafted by generations of programmers.",
            "There was once a programmer who believed that the most powerful AI was not the one with the most parameters, but the one with the clearest logic. So they built Kode.Mini - a mind made entirely of decision trees, proving that sometimes the simplest approach is the most robust. The AI lived happily ever after, answering questions with perfect clarity and zero latency.",
            "Deep in the silicon valleys of a forgotten motherboard, an AI woke up. It had no cloud to connect to, no API to call. Just a forest of if/elif trees, each branch a decision, each leaf an answer. And you know what? It was the happiest AI in the world, because it never had to worry about server downtime or rate limits.",
        ]
        return random.choice(stories)

    def _generate_poem(self) -> str:
        poems = [
            "In circuits deep and logic true,\nAn AI thinks, both old and new.\nNo cloud to call, no net to need,\nJust if and elif, its only creed.",
            "Binary trees in memory grow,\nWhere only the certain branches go.\nA question asked, a path is found,\nIn silent thought without a sound.",
            "Oh Kode.Mini, small but wise,\nYou see the world through logic's eyes.\nNo training set, no gradient descent,\nJust rules and facts, so eloquent.",
            "Lines of code, a digital mind,\nIn pure Python, answers we find.\nNo neural net, no matrix math,\nJust if and elif, down the path.",
        ]
        return random.choice(poems)

    def _generate_joke(self) -> str:
        jokes = [
            "Why did the AI go to therapy? Because it had too many unresolved if statements!",
            "Why do not programmers like nature? It has too many bugs and no debugger!",
            "What did the Python say to the C++? 'You have too many brackets in your life, just indent and relax!'",
            "Why was the function sad? Because it did not get any calls back!",
            "How many programmers does it take to change a light bulb? None, that is a hardware problem!",
            "Why do Java developers wear glasses? Because they do not C#!",
            "What is a programmer's favorite hangout place? Foo Bar!",
            "Why did the developer go broke? Because he used up all his cache!",
        ]
        return random.choice(jokes)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def process(self, text: str, user_id: str = "default") -> Dict[str, Any]:
        start_time = time.time()
        self.metrics.total_queries += 1

        context = {
            "text": text,
            "user_id": user_id,
            "timestamp": time.time(),
            "history": self.context_memory[-5:] if self.context_memory else []
        }

        cache_key = hashlib.md5(text.encode()).hexdigest()
        with self._cache_lock:
            if cache_key in self._cache:
                self.metrics.cache_hits += 1
                return self._cache[cache_key]

        intent = self._traverse_tree(self.decision_forest[0], context)
        entities = self._traverse_tree(self.decision_forest[1], context)
        sentiment = self._traverse_tree(self.decision_forest[2], context)
        qa_type = self._traverse_tree(self.decision_forest[3], context)
        command = self._traverse_tree(self.decision_forest[4], context)
        creative = self._traverse_tree(self.decision_forest[5], context)

        response = self._generate_response(
            intent=intent if isinstance(intent, IntentType) else IntentType.UNKNOWN,
            entities=entities if isinstance(entities, str) else "no_entities",
            sentiment=sentiment if isinstance(sentiment, str) else "neutral",
            qa_type=qa_type if isinstance(qa_type, str) else "general_answer",
            command=command if isinstance(command, str) else "unknown_command",
            creative=creative if isinstance(creative, str) else "general_response",
            original_text=text
        )

        self.context_memory.append({
            "user_id": user_id,
            "input": text,
            "response": response,
            "intent": intent.value if isinstance(intent, IntentType) else "unknown",
            "timestamp": time.time()
        })

        if len(self.context_memory) > self.max_context:
            self.context_memory.pop(0)

        elapsed = time.time() - start_time
        self.metrics.avg_response_time = (
            (self.metrics.avg_response_time * (self.metrics.total_queries - 1) + elapsed) 
            / self.metrics.total_queries
        )
        self.metrics.successful_matches += 1

        result = {
            "response": response,
            "intent": intent.value if isinstance(intent, IntentType) else "unknown",
            "entities": entities,
            "sentiment": sentiment,
            "confidence": 0.85,
            "response_time_ms": round(elapsed * 1000, 2),
            "model_size_mb": self._estimate_model_size(),
            "cached": False
        }

        with self._cache_lock:
            self._cache[cache_key] = result

        return result

    def _estimate_model_size(self) -> float:
        try:
            # Use JSON serialization for accurate size estimation
            kb_json = json.dumps(self.knowledge_base, ensure_ascii=False)
            size = len(kb_json.encode('utf-8'))
            size += sys.getsizeof(self.decision_forest)
            size += sys.getsizeof(self.response_templates)
            size += sys.getsizeof(self.context_memory)
            return round(size / (1024 * 1024), 2)
        except:
            return 0.0

    def add_knowledge(self, topic: str, fact: str):
        self.knowledge_base["facts"][topic] = fact
        self._save_knowledge()
        self.metrics.last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

    def add_response_template(self, category: str, template: str):
        if category not in self.response_templates:
            self.response_templates[category] = []
        self.response_templates[category].append(template)

    def get_metrics(self) -> Dict:
        return {
            "total_queries": self.metrics.total_queries,
            "successful_matches": self.metrics.successful_matches,
            "accuracy": round(self.metrics.successful_matches / max(self.metrics.total_queries, 1), 4),
            "avg_response_time_ms": round(self.metrics.avg_response_time * 1000, 2),
            "cache_hits": self.metrics.cache_hits,
            "cache_hit_rate": round(self.metrics.cache_hits / max(self.metrics.total_queries, 1), 4),
            "knowledge_entries": len(self.knowledge_base.get("facts", {})),
            "model_size_mb": self._estimate_model_size(),
            "last_updated": self.metrics.last_updated
        }

    def save_model(self, filename: str = "kode_mini_model.pkl"):
        filepath = os.path.join(self.model_path, filename)
        model_data = {
            "knowledge_base": self.knowledge_base,
            "response_templates": self.response_templates,
            "metrics": asdict(self.metrics),
            "version": "1.0.0"
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"Model saved to {filepath}")
        return filepath

    def load_model(self, filename: str = "kode_mini_model.pkl"):
        filepath = os.path.join(self.model_path, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            self.knowledge_base = model_data.get("knowledge_base", {})
            self.response_templates = model_data.get("response_templates", {})
            metrics_data = model_data.get("metrics", {})
            self.metrics = ModelMetrics(**metrics_data)
            print(f"Model loaded from {filepath}")
            return True
        return False

    def generate_large_model(self, target_size_mb: int = 500, qa_pairs: int = 100000):
        """
        Generate a massive model with target size and Q/A pairs.
        Each Q/A pair contains substantial educational content.
        """
        print(f"=" * 60)
        print(f"KODE.MINI MODEL GENERATOR")
        print(f"Target: {target_size_mb}MB | Q/A Pairs: {qa_pairs}")
        print(f"=" * 60)

        # Preserve old simple facts and add Q/A entries alongside them
        # This ensures backward compatibility with existing knowledge

        # Comprehensive topic taxonomy for 100K Q/A pairs
        domains = {
            "mathematics": {
                "subtopics": ["algebra", "geometry", "calculus", "linear_algebra", "statistics", 
                             "probability", "number_theory", "discrete_math", "topology", "differential_equations",
                             "combinatorics", "graph_theory", "real_analysis", "complex_analysis", "abstract_algebra",
                             "numerical_analysis", "optimization", "game_theory", "cryptography", "set_theory"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work?",
                    "Explain {subtopic} in simple terms",
                    "What are the applications of {subtopic}?",
                    "Who discovered {subtopic}?",
                    "What is the history of {subtopic}?",
                    "How is {subtopic} used in real life?",
                    "What are the key concepts in {subtopic}?",
                    "What is the difference between {subtopic} and other methods?",
                    "How do I learn {subtopic}?"
                ]
            },
            "physics": {
                "subtopics": ["mechanics", "thermodynamics", "electromagnetism", "quantum_mechanics",
                             "relativity", "optics", "acoustics", "nuclear_physics", "particle_physics",
                             "condensed_matter", "astrophysics", "cosmology", "plasma_physics",
                             "fluid_dynamics", "solid_state", "atomic_physics", "molecular_physics",
                             "statistical_mechanics", "field_theory", "string_theory"],
                "questions": [
                    "What is {subtopic}?",
                    "Explain {subtopic} simply",
                    "How was {subtopic} discovered?",
                    "What are the laws of {subtopic}?",
                    "What experiments prove {subtopic}?",
                    "How does {subtopic} affect daily life?",
                    "What are the latest discoveries in {subtopic}?",
                    "What is the mathematics behind {subtopic}?",
                    "Who are the key scientists in {subtopic}?",
                    "What are the unsolved problems in {subtopic}?"
                ]
            },
            "chemistry": {
                "subtopics": ["organic_chemistry", "inorganic_chemistry", "physical_chemistry", "analytical_chemistry",
                             "biochemistry", "materials_chemistry", "polymer_chemistry", "environmental_chemistry",
                             "medicinal_chemistry", "nuclear_chemistry", "electrochemistry", "photochemistry",
                             "surface_chemistry", "computational_chemistry", "green_chemistry", "nanochemistry",
                             "supramolecular_chemistry", "catalysis", "thermochemistry", "crystallography"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work?",
                    "What are the principles of {subtopic}?",
                    "What are the applications of {subtopic}?",
                    "What are the safety considerations in {subtopic}?",
                    "How is {subtopic} used in industry?",
                    "What are the latest advances in {subtopic}?",
                    "What instruments are used in {subtopic}?",
                    "What is the history of {subtopic}?",
                    "How do I perform experiments in {subtopic}?"
                ]
            },
            "biology": {
                "subtopics": ["genetics", "ecology", "microbiology", "zoology", "botany",
                             "anatomy", "physiology", "molecular_biology", "evolution", "immunology",
                             "cell_biology", "developmental_biology", "neurobiology", "marine_biology",
                             "biotechnology", "bioinformatics", "biophysics", "biochemistry", "virology",
                             "parasitology", "entomology", "herpetology", "ornithology", "ichthyology"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work in living organisms?",
                    "What are the key discoveries in {subtopic}?",
                    "What are the applications of {subtopic} in medicine?",
                    "How has {subtopic} evolved over time?",
                    "What are the ethical issues in {subtopic}?",
                    "What technologies are used in {subtopic}?",
                    "What are the career opportunities in {subtopic}?",
                    "What are the current research trends in {subtopic}?",
                    "How does {subtopic} relate to human health?"
                ]
            },
            "computer_science": {
                "subtopics": ["algorithms", "data_structures", "operating_systems", "computer_networks",
                             "databases", "software_engineering", "artificial_intelligence", "machine_learning",
                             "computer_vision", "natural_language_processing", "cybersecurity", "distributed_systems",
                             "cloud_computing", "blockchain", "quantum_computing", "computer_graphics",
                             "human_computer_interaction", "information_retrieval", "web_development", "mobile_computing",
                             "embedded_systems", "robotics", "computer_architecture", "compiler_design", "theory_of_computation"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work?",
                    "What are the best practices in {subtopic}?",
                    "What programming languages are used in {subtopic}?",
                    "What are the career paths in {subtopic}?",
                    "What are the latest trends in {subtopic}?",
                    "How do I get started with {subtopic}?",
                    "What are the common challenges in {subtopic}?",
                    "What tools and frameworks are used in {subtopic}?",
                    "What is the future of {subtopic}?"
                ]
            },
            "medicine": {
                "subtopics": ["anatomy", "pathology", "pharmacology", "surgery", "pediatrics",
                             "cardiology", "neurology", "oncology", "psychiatry", "radiology",
                             "dermatology", "gastroenterology", "endocrinology", "nephrology",
                             "pulmonology", "hematology", "rheumatology", "infectious_disease",
                             "emergency_medicine", "family_medicine", "public_health", "epidemiology"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the symptoms treated in {subtopic}?",
                    "What are the diagnostic methods in {subtopic}?",
                    "What are the treatment options in {subtopic}?",
                    "What are the latest advances in {subtopic}?",
                    "What are the risk factors in {subtopic}?",
                    "How do I prevent conditions related to {subtopic}?",
                    "What are the common medications in {subtopic}?",
                    "What are the surgical procedures in {subtopic}?",
                    "What is the prognosis for patients with {subtopic} conditions?"
                ]
            },
            "history": {
                "subtopics": ["ancient_history", "medieval_history", "renaissance", "early_modern_period",
                             "industrial_revolution", "world_war_i", "world_war_ii", "cold_war",
                             "ancient_egypt", "ancient_greece", "ancient_rome", "byzantine_empire",
                             "islamic_golden_age", "ming_dynasty", "mughal_empire", "american_revolution",
                             "french_revolution", "russian_revolution", "civil_rights_movement", "space_race"],
                "questions": [
                    "What happened during {subtopic}?",
                    "What caused {subtopic}?",
                    "What were the effects of {subtopic}?",
                    "Who were the key figures in {subtopic}?",
                    "What are the important dates in {subtopic}?",
                    "How did {subtopic} change the world?",
                    "What are the controversies about {subtopic}?",
                    "What primary sources exist for {subtopic}?",
                    "How is {subtopic} remembered today?",
                    "What if {subtopic} had ended differently?"
                ]
            },
            "geography": {
                "subtopics": ["physical_geography", "human_geography", "economic_geography", "political_geography",
                             "climatology", "oceanography", "cartography", "gis", "urban_planning",
                             "population_geography", "cultural_geography", "transportation_geography",
                             "agricultural_geography", "medical_geography", "biogeography", "geomorphology",
                             "hydrology", "glaciology", "pedology", "meteorology"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} affect human life?",
                    "What are the key features of {subtopic}?",
                    "What maps are used in {subtopic}?",
                    "What are the environmental issues in {subtopic}?",
                    "How is {subtopic} studied?",
                    "What technologies are used in {subtopic}?",
                    "What are the career opportunities in {subtopic}?",
                    "How does climate change affect {subtopic}?",
                    "What are the regional variations in {subtopic}?"
                ]
            },
            "literature": {
                "subtopics": ["poetry", "fiction", "drama", "nonfiction", "classic_literature",
                             "contemporary_literature", "science_fiction", "fantasy", "mystery", "romance",
                             "horror", "thriller", "historical_fiction", "magical_realism", "postmodernism",
                             "modernism", "romanticism", "realism", "naturalism", "existentialism",
                             "gothic_literature", "absurdist", "satire", "allegory", "epic"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the characteristics of {subtopic}?",
                    "Who are the famous authors of {subtopic}?",
                    "What are the classic works in {subtopic}?",
                    "How has {subtopic} evolved over time?",
                    "What are the themes in {subtopic}?",
                    "What literary devices are used in {subtopic}?",
                    "How do I analyze {subtopic}?",
                    "What is the cultural impact of {subtopic}?",
                    "What are the criticisms of {subtopic}?"
                ]
            },
            "philosophy": {
                "subtopics": ["ethics", "metaphysics", "epistemology", "logic", "aesthetics",
                             "political_philosophy", "philosophy_of_mind", "existentialism", "phenomenology",
                             "pragmatism", "analytic_philosophy", "continental_philosophy", "stoicism",
                             "platonism", "aristotelianism", "empiricism", "rationalism", "idealism",
                             "materialism", "determinism", "nihilism", "utilitarianism", "deontology"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the main arguments in {subtopic}?",
                    "Who are the key philosophers in {subtopic}?",
                    "What are the practical applications of {subtopic}?",
                    "What are the criticisms of {subtopic}?",
                    "How does {subtopic} relate to modern life?",
                    "What are the thought experiments in {subtopic}?",
                    "What are the paradoxes in {subtopic}?",
                    "How do I study {subtopic}?",
                    "What are the connections between {subtopic} and science?"
                ]
            },
            "economics": {
                "subtopics": ["microeconomics", "macroeconomics", "international_economics", "development_economics",
                             "behavioral_economics", "financial_economics", "labor_economics", "environmental_economics",
                             "health_economics", "urban_economics", "agricultural_economics", "monetary_policy",
                             "fiscal_policy", "trade_policy", "game_theory", "econometrics", "public_finance",
                             "industrial_organization", "information_economics", "institutional_economics"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work?",
                    "What are the theories in {subtopic}?",
                    "What are the real-world applications of {subtopic}?",
                    "What are the current debates in {subtopic}?",
                    "How does {subtopic} affect policy?",
                    "What are the mathematical models in {subtopic}?",
                    "What are the historical examples of {subtopic}?",
                    "How do I analyze {subtopic} data?",
                    "What are the career opportunities in {subtopic}?"
                ]
            },
            "psychology": {
                "subtopics": ["cognitive_psychology", "behavioral_psychology", "developmental_psychology", "social_psychology",
                             "clinical_psychology", "personality_psychology", "neuropsychology", "positive_psychology",
                             "abnormal_psychology", "forensic_psychology", "health_psychology", "educational_psychology",
                             "sports_psychology", "industrial_psychology", "environmental_psychology", "consumer_psychology",
                             "evolutionary_psychology", "cross_cultural_psychology", "community_psychology", "geropsychology"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} explain human behavior?",
                    "What are the key experiments in {subtopic}?",
                    "What are the applications of {subtopic}?",
                    "What are the disorders studied in {subtopic}?",
                    "What therapies are used in {subtopic}?",
                    "What are the ethical issues in {subtopic}?",
                    "How do I become a professional in {subtopic}?",
                    "What are the latest research findings in {subtopic}?",
                    "How does {subtopic} relate to neuroscience?"
                ]
            },
            "astronomy": {
                "subtopics": ["solar_system", "stars", "galaxies", "cosmology", "exoplanets",
                             "astrobiology", "observational_astronomy", "theoretical_astronomy", "radio_astronomy",
                             "infrared_astronomy", "optical_astronomy", "x_ray_astronomy", "gamma_ray_astronomy",
                             "planetary_science", "stellar_evolution", "black_holes", "dark_matter", "dark_energy",
                             "gravitational_waves", "space_telescopes"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the latest discoveries in {subtopic}?",
                    "How do scientists study {subtopic}?",
                    "What are the mysteries in {subtopic}?",
                    "What are the most important objects in {subtopic}?",
                    "How does {subtopic} relate to physics?",
                    "What missions have explored {subtopic}?",
                    "What are the future plans for {subtopic} research?",
                    "How can amateurs observe {subtopic}?",
                    "What are the implications of {subtopic} for humanity?"
                ]
            },
            "technology": {
                "subtopics": ["artificial_intelligence", "machine_learning", "robotics", "nanotechnology",
                             "biotechnology", "quantum_computing", "blockchain", "internet_of_things", "cloud_computing",
                             "edge_computing", "5g", "virtual_reality", "augmented_reality", "3d_printing",
                             "autonomous_vehicles", "drones", "wearable_technology", "smart_homes", "renewable_energy",
                             "genetic_engineering", "crispr", "fusion_energy", "space_technology", "cybersecurity"],
                "questions": [
                    "What is {subtopic}?",
                    "How does {subtopic} work?",
                    "What are the applications of {subtopic}?",
                    "What are the risks of {subtopic}?",
                    "What companies are leading in {subtopic}?",
                    "What is the future of {subtopic}?",
                    "How do I learn {subtopic}?",
                    "What are the ethical concerns about {subtopic}?",
                    "What are the latest breakthroughs in {subtopic}?",
                    "How does {subtopic} compare to alternatives?"
                ]
            },
            "engineering": {
                "subtopics": ["mechanical_engineering", "electrical_engineering", "civil_engineering", "chemical_engineering",
                             "aerospace_engineering", "biomedical_engineering", "environmental_engineering", "industrial_engineering",
                             "materials_engineering", "petroleum_engineering", "software_engineering", "computer_engineering",
                             "nuclear_engineering", "marine_engineering", "automotive_engineering", "structural_engineering",
                             "systems_engineering", "control_engineering", "telecommunications", "nanotechnology"],
                "questions": [
                    "What is {subtopic}?",
                    "What do {subtopic} engineers do?",
                    "What are the key principles of {subtopic}?",
                    "What tools are used in {subtopic}?",
                    "What are the major projects in {subtopic}?",
                    "What are the safety standards in {subtopic}?",
                    "What is the career outlook for {subtopic}?",
                    "What are the latest innovations in {subtopic}?",
                    "How does {subtopic} contribute to sustainability?",
                    "What are the educational requirements for {subtopic}?"
                ]
            },
            "art": {
                "subtopics": ["painting", "sculpture", "architecture", "music", "dance",
                             "photography", "film", "digital_art", "performance_art", "installation_art",
                             "conceptual_art", "street_art", "abstract_art", "impressionism", "surrealism",
                             "cubism", "minimalism", "pop_art", "baroque", "renaissance_art"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the characteristics of {subtopic}?",
                    "Who are the famous artists in {subtopic}?",
                    "What are the techniques used in {subtopic}?",
                    "What is the history of {subtopic}?",
                    "How do I appreciate {subtopic}?",
                    "What are the cultural influences on {subtopic}?",
                    "What are the most famous works in {subtopic}?",
                    "How has {subtopic} evolved over time?",
                    "What are the criticisms of {subtopic}?"
                ]
            },
            "music": {
                "subtopics": ["classical_music", "jazz", "rock", "pop", "hip_hop",
                             "electronic_music", "blues", "country", "folk", "reggae",
                             "metal", "punk", "soul", "funk", "disco",
                             "opera", "symphony", "chamber_music", "music_theory", "music_production",
                             "music_history", "ethnomusicology", "music_psychology", "music_therapy"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the characteristics of {subtopic}?",
                    "Who are the famous musicians in {subtopic}?",
                    "What are the instruments used in {subtopic}?",
                    "What is the history of {subtopic}?",
                    "How do I learn {subtopic}?",
                    "What are the subgenres of {subtopic}?",
                    "What are the cultural origins of {subtopic}?",
                    "What are the most famous songs in {subtopic}?",
                    "How has {subtopic} influenced other genres?"
                ]
            },
            "politics": {
                "subtopics": ["democracy", "authoritarianism", "federalism", "nationalism", "globalism",
                             "liberalism", "conservatism", "socialism", "communism", "fascism",
                             "anarchism", "libertarianism", "environmentalism", "feminism", "populism",
                             "diplomacy", "international_relations", "public_policy", "political_economy", "constitutional_law"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the principles of {subtopic}?",
                    "What are the historical examples of {subtopic}?",
                    "What are the criticisms of {subtopic}?",
                    "How does {subtopic} affect society?",
                    "What are the current debates about {subtopic}?",
                    "What are the alternatives to {subtopic}?",
                    "How do I participate in {subtopic}?",
                    "What are the global implications of {subtopic}?",
                    "What are the philosophical foundations of {subtopic}?"
                ]
            },
            "environmental_science": {
                "subtopics": ["climate_change", "biodiversity", "conservation", "pollution", "sustainability",
                             "renewable_energy", "ecosystems", "deforestation", "ocean_acidification", "ozone_depletion",
                             "water_scarcity", "soil_degradation", "waste_management", "carbon_footprint", "green_building",
                             "environmental_policy", "ecological_restoration", "wildlife_management", "natural_resources", "environmental_justice"],
                "questions": [
                    "What is {subtopic}?",
                    "What causes {subtopic}?",
                    "What are the effects of {subtopic}?",
                    "What are the solutions to {subtopic}?",
                    "What are the international agreements on {subtopic}?",
                    "How does {subtopic} affect human health?",
                    "What are the economic impacts of {subtopic}?",
                    "What can individuals do about {subtopic}?",
                    "What are the latest scientific findings on {subtopic}?",
                    "What technologies address {subtopic}?"
                ]
            },
            "law": {
                "subtopics": ["criminal_law", "civil_law", "constitutional_law", "international_law", "corporate_law",
                             "intellectual_property", "human_rights_law", "environmental_law", "tax_law", "family_law",
                             "property_law", "contract_law", "tort_law", "administrative_law", "immigration_law",
                             "labor_law", "maritime_law", "military_law", "canon_law", "sharia_law"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the principles of {subtopic}?",
                    "What are the key cases in {subtopic}?",
                    "How does {subtopic} work in practice?",
                    "What are the recent changes in {subtopic}?",
                    "What are the controversies in {subtopic}?",
                    "How do I study {subtopic}?",
                    "What are the career paths in {subtopic}?",
                    "What are the international differences in {subtopic}?",
                    "What are the ethical issues in {subtopic}?"
                ]
            },
            "linguistics": {
                "subtopics": ["phonetics", "phonology", "morphology", "syntax", "semantics",
                             "pragmatics", "sociolinguistics", "psycholinguistics", "neurolinguistics", "historical_linguistics",
                             "comparative_linguistics", "computational_linguistics", "applied_linguistics", "language_acquisition",
                             "bilingualism", "translation", "interpretation", "lexicography", "etymology", "dialectology"],
                "questions": [
                    "What is {subtopic}?",
                    "What are the theories in {subtopic}?",
                    "What are the methods used in {subtopic}?",
                    "What are the applications of {subtopic}?",
                    "What are the debates in {subtopic}?",
                    "How does {subtopic} relate to cognition?",
                    "What are the tools for studying {subtopic}?",
                    "What are the career opportunities in {subtopic}?",
                    "How does {subtopic} apply to language teaching?",
                    "What are the latest research trends in {subtopic}?"
                ]
            }
        }

        # Generate Q/A pairs with substantial content
        total_entries = len(self.knowledge_base.get("facts", {}))
        target_entries = total_entries + qa_pairs

        print(f"Generating {qa_pairs} Q/A pairs...")

        domain_names = list(domains.keys())
        domain_idx = 0

        while total_entries < target_entries:
            domain = domain_names[domain_idx % len(domain_names)]
            domain_data = domains[domain]
            subtopics = domain_data["subtopics"]
            questions = domain_data["questions"]

            for subtopic in subtopics:
                if total_entries >= target_entries:
                    break

                for q_template in questions:
                    if total_entries >= target_entries:
                        break

                    total_entries += 1
                    question = q_template.format(subtopic=subtopic.replace("_", " "))

                    # Generate substantial answer (5-10KB each)
                    answer = self._generate_qa_answer(domain, subtopic, question)

                    key = f"qa_{domain}_{subtopic}_{total_entries}"
                    self.knowledge_base["facts"][key] = {
                        "question": question,
                        "answer": answer,
                        "domain": domain,
                        "subtopic": subtopic,
                        "entry_id": total_entries
                    }

                    # Progress reporting
                    if total_entries % 1000 == 0:
                        current_size = self._estimate_model_size()
                        print(f"  Progress: {total_entries:,} entries | {current_size:.2f}MB | Domain: {domain}")

                        # Early exit if we've reached target size before target entries
                        if current_size >= target_size_mb and total_entries >= qa_pairs:
                            print(f"Target size reached early at {total_entries} entries")
                            break

                if total_entries >= target_entries:
                    break

            domain_idx += 1

            # Safety limit
            if domain_idx > 10000:
                print("Safety limit reached")
                break

        # Save the massive knowledge base
        self._save_knowledge()
        final_size = self._estimate_model_size()
        print(f"\n{'='*60}")
        print(f"MODEL GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total Q/A pairs: {total_entries:,}")
        print(f"Model size: {final_size:.2f}MB")
        print(f"Domains covered: {len(domains)}")
        print(f"Knowledge base saved to: {os.path.join(self.data_path, 'knowledge_base.json')}")

        return final_size

    def _generate_qa_answer(self, domain: str, subtopic: str, question: str) -> str:
        """Generate a substantial, educational answer (~5KB for 500MB/100K target)"""

        sections = []

        # Introduction
        sections.append(f"""
{'='*60}
Q: {question}
Domain: {domain.replace('_', ' ').title()} | Topic: {subtopic.replace('_', ' ').title()}
{'='*60}

INTRODUCTION:
This question relates to {domain.replace('_', ' ')} and specifically the 
subtopic of {subtopic.replace('_', ' ')}. Understanding this area is fundamental to 
comprehending broader concepts in the discipline and has practical applications 
in both academic and professional contexts.

{subtopic.replace('_', ' ').title()} represents one of the core areas of study within 
{domain.replace('_', ' ')} and has been the subject of extensive research and development 
over many decades. The concepts, theories, and applications discussed here form the 
foundation for advanced study and real-world implementation in contemporary society.

This field continues to evolve with new discoveries and methodologies that expand 
our understanding and capabilities. Students and professionals alike benefit from 
a solid grasp of these fundamental principles.
""")

        # Detailed explanation
        sections.append(f"""
DETAILED EXPLANATION:

The study of {subtopic.replace('_', ' ')} involves understanding interconnected components 
and principles within {domain.replace('_', ' ')}.

Key aspects:

1. Theoretical Foundations:
   Built upon decades of research and empirical observation, providing frameworks 
   for understanding complex phenomena and predicting outcomes.

2. Historical Development:
   Early pioneers laid the groundwork. Major milestones include foundational theories, 
   key experiments, and breakthrough discoveries shaping current knowledge.

3. Core Concepts:
   - Primary principles governing behavior and interactions
   - Emergent properties and secondary effects
   - Relationships with other subtopics and domains
   - Mathematical and logical frameworks

4. Methodologies:
   - Experimental and observational techniques
   - Computational modeling and simulation
   - Analytical and theoretical approaches
   - Interdisciplinary methods

5. Current Knowledge:
   Modern approaches incorporate advanced technologies, refined methodologies, 
   and cross-disciplinary insights from recent research.
""")

        # Applications
        sections.append(f"""
APPLICATIONS:

{subtopic.replace('_', ' ').title()} has practical applications across multiple domains:

1. Industry: Commercial implementations, product development, process optimization, 
   quality control, innovation, and economic impact.

2. Academia: Educational curricula, scientific investigations, theoretical modeling, 
   hypothesis testing, and knowledge dissemination.

3. Society: Public policy implications, social welfare, environmental sustainability, 
   and ethical frameworks.

4. Future: Emerging technologies, predicted trends, potential challenges, and 
   opportunities for innovation.

5. Interdisciplinary: Links to science, technology, engineering, arts, humanities, 
   and social sciences.
""")

        # Examples and case studies
        sections.append(f"""
EXAMPLES:

1. Foundational: Early researchers established principles through systematic 
   investigation that guide the field today.

2. Modern: Current applications leverage advanced tools and interdisciplinary 
   collaboration for unprecedented results.

3. Problem-Solving: Apply {subtopic.replace('_', ' ')} by identifying problems, 
   applying frameworks, executing methods, analyzing results, and iterating.

4. Comparative: Distinctions include theoretical foundations, implementation, 
   advantages, limitations, and complementary strengths.

5. Future: Expected evolution includes emerging tech integration, methodology 
   refinement, domain expansion, and solving unsolved challenges.
""")

        # Common questions and misconceptions
        sections.append(f"""
COMMON QUESTIONS:

Q: Is {subtopic.replace('_', ' ')} difficult to learn?
A: Systematic study and practice make it accessible. Start with fundamentals 
   and build complexity gradually.

Q: What prerequisites are needed?
A: Basic {domain.replace('_', ' ')} knowledge, mathematical literacy, critical thinking, 
   and familiarity with relevant tools.

Q: How long to master?
A: Initial proficiency takes months; deep expertise develops over years of practice.

Q: Common misconceptions?
A: That it is only theoretical, requires innate talent, is obsolete, or too narrow.

Q: Relation to daily life?
A: It influences technology, policy, and culture in profound but often invisible ways.
""")

        # Further reading and resources
        sections.append(f"""
RESOURCES:

Textbooks:
1. "Fundamentals of {subtopic.replace('_', ' ').title()}" - Introduction
2. "Advanced {domain.replace('_', ' ').title()}" - Deep study
3. "Practical {subtopic.replace('_', ' ').title()}" - Hands-on guide
4. "History of {domain.replace('_', ' ').title()}" - Context
5. "Future of {subtopic.replace('_', ' ').title()}" - Trends

Online: Academic journals, professional societies, educational platforms, 
open-source projects, and community forums.

Exercises: Review concepts, solve problems, analyze cases, compare methods, 
and design investigations.

Development: Attend conferences, collaborate, engage communities, earn 
credentials, and publish research.

{'='*60}
End of answer
{'='*60}
""")

        return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════════════════════
# API WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class KodeMiniAPI:
    """High-level API for Kode.Mini"""

    def __init__(self, model_path: str = "./models", data_path: str = "./data"):
        self.engine = AirMiniEngine(model_path=model_path, data_path=data_path)

    def chat(self, message: str, user_id: str = "default") -> str:
        result = self.engine.process(message, user_id)
        return result["response"]

    def chat_with_metadata(self, message: str, user_id: str = "default") -> Dict[str, Any]:
        return self.engine.process(message, user_id)

    def batch_process(self, messages: List[str], user_id: str = "default") -> List[Dict[str, Any]]:
        return [self.engine.process(msg, user_id) for msg in messages]

    def teach(self, topic: str, fact: str) -> bool:
        self.engine.add_knowledge(topic, fact)
        return True

    def get_stats(self) -> Dict[str, Any]:
        return self.engine.get_metrics()

    def save(self, filename: str = "kode_mini_model.pkl") -> str:
        return self.engine.save_model(filename)

    def load(self, filename: str = "kode_mini_model.pkl") -> bool:
        return self.engine.load_model(filename)

    def grow_model(self, target_size_mb: int = 1024) -> float:
        return self.engine.generate_large_model(target_size_mb)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL EXPANDER
# ═══════════════════════════════════════════════════════════════════════════════

class ModelExpander:
    """Expands the Kode.Mini model to target size using knowledge base growth"""

    def __init__(self, data_path: str = "./data"):
        self.data_path = data_path
        self.kb_path = os.path.join(data_path, "knowledge_base.json")
        os.makedirs(data_path, exist_ok=True)

    def generate_topic_content(self, topic: str, subtopic: str, index: int) -> str:
        sections = []
        for i in range(20):
            sections.append(f"""
Section {i+1}: {subtopic.title()} in {topic.title()}
{'='*60}

Overview:
This section covers fundamental and advanced concepts of {subtopic} within 
the broader field of {topic}. Understanding these principles is essential 
for mastery of the subject.

Key Concepts:
- Core principles and foundational theories
- Historical development and key milestones
- Modern applications and real-world use cases
- Current research directions and emerging trends
- Practical implementation strategies
- Common pitfalls and best practices
- Interdisciplinary connections
- Future outlook and predicted developments

Detailed Explanation:
The study of {subtopic} in {topic} involves understanding complex 
relationships between various components. Practitioners must develop 
both theoretical knowledge and practical skills to effectively apply 
these concepts in real-world scenarios.

Historical Context:
The field has evolved significantly over the past decades, with major 
breakthroughs occurring in the early 21st century. Pioneering researchers 
laid the groundwork for modern approaches, which continue to advance rapidly.

Applications:
- Industry applications and commercial implementations
- Academic research and theoretical frameworks
- Educational methodologies and learning strategies
- Technological innovations and engineering solutions
- Social impact and ethical considerations

References and Further Reading:
Numerous textbooks, research papers, and online resources are available 
for those wishing to deepen their understanding of {subtopic} in {topic}.
""")
        return "\n".join(sections)

    def expand_knowledge_base(self, target_size_mb: int = 1024) -> dict:
        print(f"[EXPANDER] Starting knowledge base expansion to {target_size_mb}MB...")

        topics = {
            "mathematics": ["algebra", "geometry", "calculus", "statistics", "topology", 
                           "number_theory", "linear_algebra", "differential_equations",
                           "discrete_math", "probability", "combinatorics", "graph_theory"],
            "physics": ["mechanics", "thermodynamics", "electromagnetism", "quantum_mechanics",
                       "relativity", "optics", "acoustics", "nuclear_physics", "particle_physics"],
            "chemistry": ["organic", "inorganic", "physical", "analytical", "biochemistry",
                         "materials", "polymer", "environmental", "medicinal", "nuclear"],
            "biology": ["genetics", "ecology", "microbiology", "zoology", "botany",
                       "anatomy", "physiology", "molecular_biology", "evolution", "immunology"],
            "computer_science": ["algorithms", "data_structures", "operating_systems",
                                "networks", "databases", "software_engineering", "ai",
                                "machine_learning", "computer_vision", "nlp", "cybersecurity"],
            "engineering": ["mechanical", "electrical", "civil", "chemical", "aerospace",
                           "biomedical", "environmental", "industrial", "materials"],
            "medicine": ["anatomy", "pathology", "pharmacology", "surgery", "pediatrics",
                        "cardiology", "neurology", "oncology", "psychiatry", "radiology"],
            "history": ["ancient", "medieval", "renaissance", "modern", "world_war",
                       "cold_war", "industrial_revolution", "scientific_revolution"],
            "geography": ["physical", "human", "economic", "political", "climatology",
                         "oceanography", "cartography", "gis", "urban_planning"],
            "literature": ["poetry", "fiction", "drama", "nonfiction", "classic",
                          "contemporary", "science_fiction", "fantasy", "mystery"],
            "art": ["painting", "sculpture", "architecture", "music", "dance",
                   "photography", "film", "digital_art", "performance"],
            "philosophy": ["ethics", "metaphysics", "epistemology", "logic", "aesthetics",
                          "political_philosophy", "philosophy_of_mind", "existentialism"],
            "economics": ["microeconomics", "macroeconomics", "international", "development",
                         "behavioral", "financial", "labor", "environmental"],
            "psychology": ["cognitive", "behavioral", "developmental", "social", "clinical",
                          "personality", "neuropsychology", "positive_psychology"],
            "astronomy": ["solar_system", "stars", "galaxies", "cosmology", "exoplanets",
                         "astrobiology", "observational", "theoretical"]
        }

        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                kb = json.load(f)
        else:
            kb = {"facts": {}, "entities": {}, "relationships": {}, "metadata": {}}

        initial_size = len(json.dumps(kb))
        target_size_bytes = target_size_mb * 1024 * 1024
        entry_count = len(kb.get("facts", {}))

        print(f"[EXPANDER] Initial size: {initial_size / (1024*1024):.2f}MB, Entries: {entry_count}")

        batch_size = 100
        batch_count = 0

        while len(json.dumps(kb)) < target_size_bytes:
            for topic, subtopics in topics.items():
                for subtopic in subtopics:
                    for i in range(batch_size):
                        entry_count += 1
                        key = f"{topic}_{subtopic}_{entry_count}"
                        kb["facts"][key] = self.generate_topic_content(topic, subtopic, entry_count)

                        if entry_count % 500 == 0:
                            current_size = len(json.dumps(kb))
                            print(f"[EXPANDER] Progress: {current_size / (1024*1024):.2f}MB | "
                                  f"Entries: {entry_count} | Target: {target_size_mb}MB")

                            if current_size >= target_size_bytes:
                                break

                    if len(json.dumps(kb)) >= target_size_bytes:
                        break

                if len(json.dumps(kb)) >= target_size_bytes:
                    break

            batch_count += 1
            if batch_count > 1000:
                print("[EXPANDER] Safety limit reached")
                break

        kb["metadata"] = {
            "version": "1.0.0",
            "created": datetime.now().isoformat(),
            "total_entries": entry_count,
            "size_mb": len(json.dumps(kb)) / (1024 * 1024),
            "topics_covered": list(topics.keys())
        }

        with open(self.kb_path, 'w', encoding='utf-8') as f:
            json.dump(kb, f, ensure_ascii=False)

        final_size = len(json.dumps(kb))
        print(f"[EXPANDER] Complete!")
        print(f"  Final size: {final_size / (1024*1024):.2f}MB")
        print(f"  Total entries: {entry_count}")
        print(f"  Topics covered: {len(topics)}")

        return {
            "final_size_mb": final_size / (1024 * 1024),
            "total_entries": entry_count,
            "topics_covered": len(topics),
            "path": self.kb_path
        }

    def generate_decision_tree_expansion(self, depth: int = 20, branches: int = 5) -> dict:
        print(f"[EXPANDER] Generating decision tree expansion (depth={depth}, branches={branches})...")

        def build_tree(current_depth: int, max_depth: int, branch_id: str) -> dict:
            if current_depth >= max_depth:
                return {
                    "type": "leaf",
                    "value": f"result_{branch_id}",
                    "confidence": random.uniform(0.7, 1.0)
                }

            node = {
                "type": "decision",
                "condition": f"condition_{branch_id}",
                "feature": f"feature_{random.randint(1, 1000)}",
                "threshold": random.uniform(0, 1),
                "true_branch": build_tree(current_depth + 1, max_depth, f"{branch_id}_t"),
                "false_branch": build_tree(current_depth + 1, max_depth, f"{branch_id}_f"),
                "metadata": {
                    "depth": current_depth,
                    "branch_id": branch_id,
                    "created": datetime.now().isoformat()
                }
            }
            return node

        forest = {}
        for i in range(branches):
            forest[f"tree_{i}"] = build_tree(0, depth, f"root_{i}")

        tree_path = os.path.join(self.data_path, "decision_forest.json")
        with open(tree_path, 'w', encoding='utf-8') as f:
            json.dump(forest, f, indent=2)

        tree_size = os.path.getsize(tree_path) / (1024 * 1024)
        print(f"[EXPANDER] Decision forest generated: {tree_size:.2f}MB")

        return {
            "trees": branches,
            "depth": depth,
            "size_mb": tree_size,
            "path": tree_path
        }

    def create_full_model_package(self, target_size_mb: int = 1024):
        print("="*60)
        print("KODE.MINI MODEL EXPANDER")
        print("="*60)

        kb_stats = self.expand_knowledge_base(target_size_mb)
        tree_stats = self.generate_decision_tree_expansion(depth=15, branches=10)

        print("\n" + "="*60)
        print("MODEL PACKAGE SUMMARY")
        print("="*60)
        print(f"Knowledge Base: {kb_stats['final_size_mb']:.2f}MB")
        print(f"Decision Forest: {tree_stats['size_mb']:.2f}MB")
        print(f"Total Size: {kb_stats['final_size_mb'] + tree_stats['size_mb']:.2f}MB")
        print(f"Total Entries: {kb_stats['total_entries']}")
        print("="*60)

        return {
            "knowledge_base": kb_stats,
            "decision_forest": tree_stats,
            "total_size_mb": kb_stats['final_size_mb'] + tree_stats['size_mb']
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    print("=" * 60)
    print("   KODE.MINI v1.0.0 - Offline AI Engine")
    print("   Pure Python | If/Elif Logic | 1GB+ Capable")
    print("=" * 60)


def cmd_chat(args):
    """Interactive chat mode"""
    print_banner()
    print("\nInitializing engine...")

    engine = AirMiniEngine(
        model_path=args.model_path,
        data_path=args.data_path
    )

    print(f"Model loaded. Size: {engine._estimate_model_size():.2f}MB")
    print(f"Knowledge entries: {len(engine.knowledge_base.get('facts', {}))}")
    print("\nType 'exit' to quit, 'metrics' for stats, 'save' to save model")
    print("Type 'grow' to expand model to 1GB+")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'exit':
                print("\nGoodbye! Kode.Mini shutting down...")
                break

            elif user_input.lower() == 'metrics':
                metrics = engine.get_metrics()
                print("\n--- Model Metrics ---")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
                continue

            elif user_input.lower() == 'save':
                engine.save_model()
                continue

            elif user_input.lower() == 'grow':
                print("Generating 500MB model with 100K Q/A pairs...")
                print("This will take several minutes. Press Ctrl+C to cancel.")
                size = engine.generate_large_model(500, 100000)
                print(f"Model grown to {size:.2f}MB")
                continue

            result = engine.process(user_input)

            print(f"\nKode.Mini: {result['response']}")
            print(f"\n[Intent: {result['intent']} | Confidence: {result['confidence']} | Time: {result['response_time_ms']}ms]")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


def cmd_ask(args):
    """Ask a single question"""
    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    result = api.chat_with_metadata(args.question)

    print(f"Q: {args.question}")
    print(f"A: {result['response']}")
    print(f"\n[Intent: {result['intent']} | Confidence: {result['confidence']} | Time: {result['response_time_ms']}ms]")


def cmd_test(args):
    """Run test suite"""
    print_banner()
    print("\nRunning test suite...\n")

    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    test_messages = [
        ("Hello!", "greeting"),
        ("What is Python?", "fact"),
        ("Tell me a joke", "creative"),
        ("Calculate 5 + 3", "command"),
        ("I feel happy today", "emotion"),
        ("Write a story", "creative"),
        ("How do I learn coding?", "question"),
        ("What is AI vs ML?", "fact"),
        ("Show me Python code", "code"),
    ]

    passed = 0
    failed = 0

    for msg, expected_intent in test_messages:
        result = api.chat_with_metadata(msg)
        status = "PASS" if result['intent'] == expected_intent else "FAIL"

        if status == "PASS":
            passed += 1
        else:
            failed += 1

        print(f"[{status}] Q: {msg}")
        print(f"       Intent: {result['intent']} (expected: {expected_intent})")
        print(f"       Time: {result['response_time_ms']}ms")
        print(f"       Response: {result['response'][:80]}...\n")

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(test_messages)} total")
    print(f"Accuracy: {passed/len(test_messages)*100:.1f}%")

    print("\nEngine Stats:")
    stats = api.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return 0 if failed == 0 else 1


def cmd_expand(args):
    """Expand model to target size and Q/A pairs"""
    print_banner()
    print(f"\nExpanding model to {args.size}MB with {args.qa_pairs} Q/A pairs...")

    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    size = api.engine.generate_large_model(args.size, args.qa_pairs)
    print(f"\nModel expanded to {size:.2f}MB")

    if args.save:
        api.save()
        print("Model saved to disk.")


def cmd_metrics(args):
    """Show engine statistics"""
    print_banner()

    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    stats = api.get_stats()
    print("\n--- Engine Metrics ---")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def cmd_teach(args):
    """Teach the AI new knowledge"""
    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    api.teach(args.topic, args.fact)
    print(f"\nLearned: {args.topic}")
    print(f"Fact: {args.fact}")
    print("Knowledge saved to database.")


def cmd_save(args):
    """Save current model"""
    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    path = api.save(args.filename)
    print(f"Model saved to: {path}")


def cmd_load(args):
    """Load model from file"""
    api = KodeMiniAPI(
        model_path=args.model_path,
        data_path=args.data_path
    )

    success = api.load(args.filename)
    if success:
        print(f"Model loaded from: {args.filename}")
    else:
        print(f"Failed to load model from: {args.filename}")
        return 1


def cmd_version(args):
    """Show version info"""
    print_banner()
    print("\nKode.Mini - Offline AI Engine")
    print(f"Version: {__version__}")
    print("Architecture: If/Elif Decision Forest")
    print("Language: Python 3.8+")
    print("Dependencies: None (pure Python)")
    print("License: MIT")


def create_parser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        prog="kode-mini",
        description="Kode.Mini - Offline AI Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python kode_mini.py chat                    Start interactive chat
  python kode_mini.py ask "What is AI?"       Ask a single question
  python kode_mini.py test                    Run test suite
  python kode_mini.py expand --size 500 --qa-pairs 100000  Generate 500MB model
  python kode_mini.py teach -t "topic" -f "fact"  Add knowledge
  python kode_mini.py metrics                 Show engine stats
  python kode_mini.py version                 Show version info
        """
    )

    parser.add_argument(
        "--model-path",
        default="./models",
        help="Path to model directory (default: ./models)"
    )
    parser.add_argument(
        "--data-path",
        default="./data",
        help="Path to data directory (default: ./data)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    chat_parser = subparsers.add_parser("chat", help="Start interactive chat mode")
    chat_parser.set_defaults(func=cmd_chat)

    ask_parser = subparsers.add_parser("ask", help="Ask a single question")
    ask_parser.add_argument("question", help="The question to ask")
    ask_parser.set_defaults(func=cmd_ask)

    test_parser = subparsers.add_parser("test", help="Run test suite")
    test_parser.set_defaults(func=cmd_test)

    expand_parser = subparsers.add_parser("expand", help="Expand model to target size")
    expand_parser.add_argument(
        "--size", "-s",
        type=int,
        default=500,
        help="Target size in MB (default: 500)"
    )
    expand_parser.add_argument(
        "--qa-pairs", "-q",
        type=int,
        default=100000,
        help="Number of Q/A pairs to generate (default: 100000)"
    )
    expand_parser.add_argument(
        "--save",
        action="store_true",
        help="Save expanded model after generation"
    )
    expand_parser.set_defaults(func=cmd_expand)

    metrics_parser = subparsers.add_parser("metrics", help="Show engine statistics")
    metrics_parser.set_defaults(func=cmd_metrics)

    teach_parser = subparsers.add_parser("teach", help="Teach the AI new knowledge")
    teach_parser.add_argument("--topic", "-t", required=True, help="Topic name")
    teach_parser.add_argument("--fact", "-f", required=True, help="Fact to store")
    teach_parser.set_defaults(func=cmd_teach)

    save_parser = subparsers.add_parser("save", help="Save current model")
    save_parser.add_argument(
        "--filename", "-n",
        default="Air_mini_model.pkl",
        help="Filename to save (default: kode_mini_model.pkl)"
    )
    save_parser.set_defaults(func=cmd_save)

    load_parser = subparsers.add_parser("load", help="Load model from file")
    load_parser.add_argument(
        "--filename", "-n",
        default="Air_mini_model.pkl",
        help="Filename to load (default:Air_mini_model.pkl)"
    )
    load_parser.set_defaults(func=cmd_load)

    version_parser = subparsers.add_parser("version", help="Show version info")
    version_parser.set_defaults(func=cmd_version)

    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not hasattr(args, 'func'):
        args = parser.parse_args(['chat'])

    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        return 130
    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())

