#!/usr/bin/env python3
"""
YouTube Transcript API Examples
Demonstrates how to fetch transcripts from YouTube videos
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import sys


def get_transcript(video_id: str, languages=['en']) -> list:
    """
    Get transcript for a YouTube video.
    
    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ' from https://youtube.com/watch?v=dQw4w9WgXcQ)
        languages: List of language codes to try (default: ['en'])
    
    Returns:
        List of transcript entries with 'text', 'start', and 'duration' fields
    """
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return transcript
    except TranscriptsDisabled:
        print(f"❌ Transcripts are disabled for video: {video_id}")
        return []
    except NoTranscriptFound:
        print(f"❌ No transcript found for video: {video_id} in languages: {languages}")
        return []
    except Exception as e:
        print(f"❌ Error fetching transcript: {e}")
        return []


def get_transcript_text_only(video_id: str, languages=['en']) -> str:
    """
    Get transcript as plain text (no timestamps).
    
    Args:
        video_id: YouTube video ID
        languages: List of language codes to try
    
    Returns:
        Full transcript as a single string
    """
    transcript = get_transcript(video_id, languages)
    if not transcript:
        return ""
    
    # Join all text segments
    full_text = " ".join([entry['text'] for entry in transcript])
    return full_text


def list_available_transcripts(video_id: str):
    """
    List all available transcripts for a video (manual and auto-generated).
    
    Args:
        video_id: YouTube video ID
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        print(f"\n📝 Available transcripts for video: {video_id}\n")
        
        # Manual transcripts
        print("Manual transcripts:")
        for transcript in transcript_list:
            if not transcript.is_generated:
                print(f"  - {transcript.language} ({transcript.language_code})")
        
        # Auto-generated transcripts
        print("\nAuto-generated transcripts:")
        for transcript in transcript_list:
            if transcript.is_generated:
                print(f"  - {transcript.language} ({transcript.language_code})")
                
    except Exception as e:
        print(f"❌ Error listing transcripts: {e}")


def extract_video_id(url: str) -> str:
    """
    Extract video ID from YouTube URL.
    
    Args:
        url: YouTube URL (e.g., https://youtube.com/watch?v=VIDEO_ID)
    
    Returns:
        Video ID string
    """
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    elif 'watch?v=' in url:
        return url.split('watch?v=')[1].split('&')[0]
    else:
        # Assume it's already a video ID
        return url


# Example usage
if __name__ == "__main__":
    # Example 1: Get transcript with timestamps
    print("=" * 60)
    print("Example 1: Get transcript with timestamps")
    print("=" * 60)
    
    video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    transcript = get_transcript(video_id)
    
    if transcript:
        print(f"\n✅ Found {len(transcript)} transcript segments\n")
        # Show first 3 segments
        for i, entry in enumerate(transcript[:3]):
            print(f"[{entry['start']:.2f}s] {entry['text']}")
        print("...")
    
    # Example 2: Get plain text transcript
    print("\n" + "=" * 60)
    print("Example 2: Get plain text transcript")
    print("=" * 60)
    
    text = get_transcript_text_only(video_id)
    if text:
        print(f"\n✅ Transcript length: {len(text)} characters")
        print(f"First 200 chars: {text[:200]}...")
    
    # Example 3: List available transcripts
    print("\n" + "=" * 60)
    print("Example 3: List available transcripts")
    print("=" * 60)
    list_available_transcripts(video_id)
    
    # Example 4: Extract from URL
    print("\n" + "=" * 60)
    print("Example 4: Extract video ID from URL")
    print("=" * 60)
    
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    extracted_id = extract_video_id(url)
    print(f"URL: {url}")
    print(f"Video ID: {extracted_id}")
    
    # Example 5: Try different languages
    print("\n" + "=" * 60)
    print("Example 5: Try multiple languages")
    print("=" * 60)
    
    # Try English first, then Spanish, then any auto-generated
    transcript = get_transcript(video_id, languages=['en', 'es', 'en-US'])
    if transcript:
        print(f"✅ Found transcript in one of the requested languages")
