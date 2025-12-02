1. The Scout Agent (The "Map Maker")
Goal: Dynamic Target Discovery The Problem: Hard-coded lists of subreddits (like just checking r/wallstreetbets) miss viral conversations happening in unexpected places (e.g., r/Gaming discussing a GPU failure, or r/ArtificialIntelligence discussing a new chip).

Core Logic:

Receives a Ticker (e.g., "NVDA").

Uses a search tool (Google Search or Reddit global search) to find the "loudest" communities discussing that ticker in the last 24 hours.

Ranks them by "Velocity" (posts per hour).

Excludes non-relevant noise (e.g., if scraping "GAP", exclude r/GapFilling).

Input: "NVDA"

Agent Thought Process: "I need to find where NVDA is trending today. I see high volume in r/Nvidia, r/Hardware, and r/investing. r/funny has one post, I will ignore that."

Output: ["r/wallstreetbets", "r/Nvidia", "r/Hardware", "r/stocks"]

2. The Query Agent (The "Translator")
Goal: Context-Aware Keyword Expansion The Problem: A simple search for "NVDA" misses critical sentiment. Investors use slang, product names, CEO nicknames, or "cashtags" that a regex script misses.

Core Logic:

Receives a Ticker.

Uses an LLM (internal knowledge) to generate a "Semantic Cloud" for that company.

Identifies:

Cashtags: $NVDA

Key People: "Jensen Huang", "Jensen"

Key Products: "Blackwell", "RTX 5090", "H100"

Slang/Memes: "Team Green", "Nancy Pelosi stock"

Formats them into a Boolean search string.

Input: "NVDA"

Agent Thought Process: "People don't just say NVDA. They talk about the new Blackwell chips and Jensen's leather jacket. I need to search for all of these to get the full picture."

Output: ['"NVDA"', '"$NVDA"', '"Jensen Huang"', '"Blackwell"', '"RTX 5090"']

3. The Hunter Agent (The "Filter")
Goal: Signal-to-Noise Purification The Problem: Scraping keyword matches brings in garbage. A post saying "My RTX 4090 drivers keep crashing, help!" contains the keywords but is useless for financial sentiment. It creates false negatives.

Core Logic:

Receives a raw list of scraped posts.

Analyzes the intent of the text.

Classifies posts into buckets:

Financial/Market: (Keep) "Earnings look good."

News/Rumor: (Keep) "New chip delayed."

Tech Support/Gamer: (Discard) "My FPS is low."

Spam/Bot: (Discard) "Join my discord."

Input: Raw CSV of 100 posts.

Agent Thought Process: "Post #1 is complaining about a video game lagging. That is irrelevant to the stock price. Delete. Post #2 is about data center revenue. Keep."

Output: A curated JSON/CSV of only high-signal, financially relevant posts.

4. The Analyst Agent (The "Narrative Builder")
Goal: Insight Synthesis The Problem: A raw sentiment score (e.g., -0.45) is just a number. It doesn't tell you why the market is bearish. You need a summary to make decisions.

Core Logic:

Receives the cleaned posts from the Hunter Agent + the FinBERT sentiment scores.

Identifies "Clusters" or themes (e.g., 50 posts talking about "delay").

Correlates sentiment with themes (e.g., "The 'delay' cluster is 90% negative").

Writes a concise executive summary citing specific posts as evidence.

Input: Cleaned Data + Sentiment Scores.

Agent Thought Process: "Sentiment is very low today. I see 40% of posts mention 'antitrust investigation'. This is the main driver. I should highlight this in the report."

Output: "Daily Report: NVDA sentiment is Bearish (-0.45). The primary driver is a rumor regarding an antitrust probe, mentioned in 34 high-velocity posts. Secondary discussions focus on excitement for the upcoming earnings call."