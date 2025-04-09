import logging
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, ImageClip
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import glob
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

export_dir = Path('/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/export')
srt_dir = Path('/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT')
exported_video_files = glob.glob(str(export_dir / '*.mp4'))
srt_files = glob.glob(str(srt_dir / '*_split.srt'))

# Define your font paths here
font_paths = {
    'CN': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/chinese.msyh.ttf',
    'HK': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/chinese.msyh.ttf',
    'KR': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Maplestory OTF Bold.otf',
    'JP': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Gen Jyuu Gothic Monospace Bold.ttf',
    'SA': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Noto Naskh Arabic-Bold.ttf',
    'TH': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Aksaramatee Bold.ttf',
    'IN': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Mangal Regular.ttf',
    'default': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/ProximaNovaSemibold.ttf'  # Default font
}

def select_font(language_code):
    return font_paths.get(language_code, font_paths['default'])

# Update languages_to_skip to only exclude 'IN' (Hindi)
languages_to_skip = ['IN']

def create_rounded_rectangle(size, radius, color):
    """Creates an image with a rounded rectangle."""
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius, fill=255)
    rounded_rect = Image.new('RGB', size, color)
    rounded_rect.putalpha(mask)
    return np.array(rounded_rect)

def create_text_clip_with_background(txt, fontsize, font_name, text_color):
    """Creates a text clip with a white rounded background."""
    # Special handling only for Arabic text
    if any('\u0600' <= char <= '\u06FF' for char in txt):
        fontsize = int(fontsize * 1.2)
        # Create PIL Image for Arabic text
        font = ImageFont.truetype(font_name, fontsize)
        temp_img = Image.new('RGBA', (1000, 200), (255, 255, 255, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), txt, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        h_padding = 70
        v_padding = 30
        img_width = text_width + h_padding
        img_height = text_height + v_padding
        
        # Create background with rounded corners
        bg = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
        bg_draw = ImageDraw.Draw(bg)
        bg_draw.rounded_rectangle([(0, 0), (img_width, img_height)], 15, fill=(255, 255, 255, 255))
        
        # Draw Arabic text from right to left
        bg_draw.text((img_width - text_width - h_padding//2, v_padding//2), 
                     txt, 
                     font=font, 
                     fill='black',
                     direction='rtl')
        
        return ImageClip(np.array(bg)).set_duration(1)
        
    else:
        # Original code for all other languages
        if any('\u0E00' <= char <= '\u0E7F' for char in txt):  # Thai
            fontsize = int(fontsize * 1.3)
        
        fontsize = max(40, min(fontsize, 80))
        
        text_clip = TextClip(
            txt, 
            fontsize=fontsize, 
            font=font_name, 
            color=text_color,
            kerning=-1,
            method='label'
        )
        
        text_width, text_height = text_clip.size
        
        # Use original padding logic
        if any('\u0E00' <= char <= '\u0E7F' for char in txt):  # Thai
            h_padding = 60
        else:
            h_padding = 50
            
        size = (text_width + h_padding, text_height + 30)
        bg_array = create_rounded_rectangle(size, radius=15, color=(255, 255, 255))
        bg_clip = ImageClip(bg_array)
        composite_clip = CompositeVideoClip([
            bg_clip.set_position(('center', 'center')), 
            text_clip.set_position(('center', 'center'))
        ], size=size)
        
        return composite_clip.set_duration(text_clip.duration)

def process_video(exported_video_file):
    video_file_name = Path(exported_video_file).name
    language_code = video_file_name.split('_')[-1].split('.')[0]
    if language_code in languages_to_skip:
        logging.info(f"Skipping language {language_code} as per configuration.")
        return

    matching_srt_file = next((srt for srt in srt_files if language_code in srt), None)
    if not matching_srt_file:
        logging.warning(f"No SRT file found for {language_code}, skipping video.")
        return
    
    logging.info(f"Found video: {video_file_name} and subtitles: {Path(matching_srt_file).name}")

    try:
        output_video_file = str(export_dir / video_file_name.replace('.mp4', '_Sub.mp4'))
        video_clip = VideoFileClip(exported_video_file)
        font_path = select_font(language_code)

        subtitles_generator = lambda txt: create_text_clip_with_background(txt, fontsize=60, font_name=font_path, text_color='black')
        subtitles_clip = SubtitlesClip(matching_srt_file, make_textclip=subtitles_generator)
        pos_y = (2 * video_clip.size[1]) // 3
        
        # Calculate the end time for subtitles (1 second before video ends instead of 3)
        subtitle_end_time = max(0, video_clip.duration - 1)
        
        # Trim the subtitles clip to end 1 second before the video ends
        subtitles_clip = subtitles_clip.subclip(0, subtitle_end_time)
        
        subtitles_clip = subtitles_clip.set_position(('center', pos_y))

        video_with_subs = CompositeVideoClip([video_clip, subtitles_clip])
        video_with_subs.write_videofile(output_video_file, codec='libx264', audio_codec='aac')

        logging.info(f"Subtitle burned into {output_video_file}")
    except Exception as e:
        logging.error(f"Failed to process video {video_file_name} due to {e}")

if __name__ == '__main__':
    if not exported_video_files:
        logging.info("No video files found in the directory.")
    elif not srt_files:
        logging.info("No subtitle files found in the directory.")
    else:
        logging.info("OK, hold on, we are getting there! 小程序正在努力运转中～")
        for video_file in exported_video_files:
            process_video(video_file)
