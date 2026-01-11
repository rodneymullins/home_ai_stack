#!/usr/bin/env python3
"""
YouTube Transcript Tool
Get transcripts without downloading videos
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import sys
import re


def extract_video_id(url_or_id):
    """Extract YouTube video ID from URL or return ID if already provided"""
    # If it's already just an ID (11 characters, alphanumeric)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Extract from various YouTube URL formats
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


def get_transcript(video_id, languages=['en']):
    """
    Get transcript for a YouTube video
    
    Args:
        video_id: YouTube video ID or URL
        languages: List of language codes to try (default: ['en'])
    
    Returns:
        dict with transcript text and metadata
    """
    vid_id = extract_video_id(video_id)
    
    if not vid_id:
        return {"error": "Invalid YouTube URL or video ID"}
    
    try:
        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(vid_id, languages=languages)
        
        # Format as plain text
        formatter = TextFormatter()
        text_transcript = formatter.format_transcript(transcript_list)
        
        # Also provide timestamped version
        timestamped = []
        for entry in transcript_list:
            mins = int(entry['start'] // 60)
            secs = int(entry['start'] % 60)
            timestamped.append(f"[{mins}:{secs:02d}] {entry['text']}")
        
        return {
            "video_id": vid_id,
            "url": f"https://youtube.com/watch?v={vid_id}",
            "transcript": text_transcript,
            "timestamped": "\\n".join(timestamped),
            "duration": transcript_list[-1]['start'] + transcript_list[-1]['duration'] if transcript_list else 0,
            "entry_count": len(transcript_list)
        }
    
    except Exception as e:
        return {"error": str(e), "video_id": vid_id}


def save_transcript(result, output_file=None):
    """Save transcript to file"""
    if "error" in result:
        print(f"Error: {result['error']}")
        return False
    
    if not output_file:
        output_file = f"{result['video_id']}_transcript.txt"
    
    with open(output_file, 'w') as f:
        f.write(f"YouTube Transcript\\n")
        f.write(f"URL: {result['url']}\\n")
        f.write(f"Duration: {int(result['duration']//60)}:{int(result['duration']%60):02d}\\n")
        f.write(f"Entries: {result['entry_count']}\\n")
        f.write("="*80 + "\\n\\n")
        f.write(result['transcript'])
    
    print(f"✅ Transcript saved to: {output_file}")
    return True


# CLI Interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python youtube_transcript_tool.py <VIDEO_URL_OR_ID> [output_file]")
        print("\\nExamples:")
        print("  python youtube_transcript_tool.py https://youtube.com/watch?v=dQw4w9WgXcQ")
        print("  python youtube_transcript_tool.py dQw4w9WgXcQ transcript.txt")
        sys.exit(1)
    
    video = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🎥 Fetching transcript for: {video}")
    result = get_transcript(video)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)
    
    # Print summary
    print(f"\\n✅ Transcript retrieved!")
    print(f"   Video ID: {result['video_id']}")
    print(f"   Duration: {int(result['duration']//60)}:{int(result['duration']%60):02d}")
    print(f"   Entries: {result['entry_count']}")
    
    if output:
        save_transcript(result, output)
    else:
        print(f"\\n--- TRANSCRIPT ---\\n")
        print(result['transcript'][:500])
        if len(result['transcript']) > 500:
            print(f"\\n... ({len(result['transcript'])-500} more characters)")
            print(f"\\nRun with output file to save full transcript")
