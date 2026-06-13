# config.py
# ─────────────────────────────────────────────
# Central configuration for Abhi-Nexus
# This is the single source of truth for all
# settings. Every agent reads from here.
# ─────────────────────────────────────────────

# News sources — each is a dictionary with:
#   name     : human readable source name
#   url      : RSS feed URL
#   category : what kind of news this source covers

NEWS_SOURCES = [
    # AI & Machine Learning
    {
        "name": "MIT AI News",
        "url": "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "category": "AI"
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "AI"
    },

    # General Tech
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage?count=20",
        "category": "General"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "General"
    },

    # Engineering
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "category": "Engineering"
    },
    {
        "name": "Stack Overflow Blog",
        "url": "https://stackoverflow.blog/feed/",
        "category": "Engineering"
    },

    # Cloud
    {
        "name": "AWS News",
        "url": "https://aws.amazon.com/blogs/aws/feed/",
        "category": "Cloud"
    },

    # Security
    {
        "name": "Krebs on Security",
        "url": "https://krebsonsecurity.com/feed/",
        "category": "Security"
    },
]

# How many articles to fetch per source
ARTICLES_PER_SOURCE = 5

# Where to store fetched data
RAW_DATA_PATH = "data/raw_articles.json"