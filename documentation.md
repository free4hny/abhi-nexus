## Phase 1
>> Fetch Agent
- Input: a list of URLs
- Job: go fetch articles from each URL
- Output: a list of article dictionaries

 ## config.py
 - Every professional pythin project has central config. Because if tomorrow you want to add a new source, change the data path, and adjust how many articles to fetch you change it in one place.
 - No hunting through 10 files.
 - e.g. in Meta, in DataSwarm, pipeline configuration lives separately from the operator code.

 ## __init__.py file
 - This file is created under "agents" folder. 
 - This file tells Python that the folder "agent" is a package, meaning you can import from it.
 - e.g. from agent.fetch_agent import fetch_all

 ## fetch_agent.py
 >> *fetch_from_source* knows how to talk to one source. Give it TechCrunch, it fetches TechCrunch. Give it AWS Blog, it fetches AWS Blog. It has no idea other sources exist.
>> *fetch_all* is the coordinator. It looks at your entire sources list, calls fetch_from_source once for each source, collects all the results, and then deduplicates them.
-- fetch_all([source1, source2, source3])
    │
    ├── calls fetch_from_source(source1) → returns [a1, a2, a3]
    ├── calls fetch_from_source(source2) → returns [b1, b2]
    ├── calls fetch_from_source(source3) → returns [c1, c2, c3]
    │
    └── combines + deduplicates → returns [a1,a2,a3,b1,b2,c1,c2,c3]

>> Why split them?*
## Two reasons:
- *First*, testability. You can test one source in isolation without running all 8. If AWS Blog is broken, you call fetch_from_source(aws_source) alone to debug it. You don't have to run the whole pipeline.
- *Second*, this is a pattern called single responsibility — each function does exactly one thing. fetch_from_source fetches one source. fetch_all coordinates many. At Meta, every Dataswarm operator follows this same principle — one operator, one job.

## The full flow in one picture:
fetch_all() called
      │
      ├─ fetch_from_source(HackerNews)
      │       │
      │       ├─ feedparser.parse(url)     ← hits internet
      │       ├─ loop entries
      │       │     ├─ make_article_id()   ← MD5 hash
      │       │     ├─ clean_text()        ← strip HTML
      │       │     ├─ parse_date()        ← normalize UTC
      │       │     └─ extract_image()     ← find thumbnail
      │       └─ returns [article1, article2, article3, article4, article5]
      │
      ├─ sleep(0.5)
      │
      ├─ fetch_from_source(ArsTechnica)
      │       └─ returns [article6, article7 ...]
      │
      ├─ ... repeat for all 8 sources ...
      │
      ├─ deduplicate by article["id"]
      │
      └─ returns final unique list → this is the CONTEXT
                                     passed to Agent 2

>> What is a master agent?
- Till now human is the coordinator who runs fetchall() directly. Its me who decide what runs, in what order and what to do if something fails.
- A master agent replaces the human and coordinates on his behalf.
    - It knows what all agents exists.
    - Decides what to run and in what order.
    - passes context from one agent to the next.
    - Handles failures and decides what to do.
    - reports status back.
* This is the difference between a pipeline and a multi-agent system. In a pipeline the order is hardcoded.
* In a multi-agent system, the master agent coordinates.

>> What the master agent looks like in plain English
    Master Agent wakes up
    │
    ├─ "My job is to produce a ranked news digest"
    │
    ├─ Step 1: "I need articles first"
    │           → calls Fetch Agent
    │           → receives context (39 articles)
    │           → checks: did I get articles? yes → continue
    │                                          no  → retry or abort
    │
    ├─ Step 2: "I need articles ranked"
    │           → calls Rank Agent (Phase 3)
    │           → receives enriched context
    │
    ├─ Step 3: "I need summaries"
    │           → calls Summary Agent (Phase 3)
    │
    ├─ Step 4: "I need to send email"
    │           → calls Email Agent
    │
    └─ "Job done. Saving state."

- Master agent does not do the actual work. It coordinates who does the work and checks the results.


>> The folder structure we are adding

    abhi-nexus/
    ├── agents/
    │   ├── __init__.py
    │   ├── fetch_agent.py     ← Phase 1 (done)
    │   └── rank_agent.py      ← Phase 3 (stub for now)
    ├── master_agent.py        ← Phase 2 (building now)
    ├── config.py
    ├── run.py
    └── data/
        └── raw_articles.json

>> What is Agent state?
- The master agent needs to track whats happening. We call this `state`.
- Here is a simple dictionary:
    state = {
    "status":        "idle",     # idle | running | done | error
    "current_step":  None,       # which agent is running now
    "articles_count": 0,         # how many articles fetched
    "errors":        [],         # list of errors encountered
    "started_at":    None,       # when the run started
    "completed_at":  None,       # when it finished
}
- This state is what a monitoring systems like CDM at Meta reads to know if your pipeline is healthy.

>> Why are we using class in master agent not just a function?
- Because Mater Agent needs to maintain `STATE` across multiple steps. A class lets us store that state on self, clean and explicit.
- A function cannot hold state between calls without ugly global variables.

>> Why to save the final enriched context to disk using `_save_context(self)`
- using this function in Master agent we are saving the context to the disk.
- The streamlit UI reads from this file
- If the server restarts data is not lost. Other processes can read the data. `This is called Persistence` a core data engineer concept.

