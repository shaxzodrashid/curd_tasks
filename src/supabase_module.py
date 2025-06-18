# Module for Supabase-related tasks
# ...existing code...

def is_supabase_url(url):
    """Check if a URL is a valid Supabase URL (very basic check)."""
    return url.startswith("https://") and "supabase.co" in url
