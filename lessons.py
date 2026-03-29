
import os
import re
import time
import subprocess
import requests

DOMAIN = 'pro.yuketang.cn'
DOWNLOAD_BASE_DIR = '/mnt/wsl/hdd/RainDownload'


def sanitize_filename(name):
    """Sanitize a filename by removing illegal characters and replacing spaces with underscores."""
    if not isinstance(name, str):
        name = str(name)
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = name.replace(' ', '_')
    return name.strip()


def launch_request(url, params=None, headers=None):
    """Launch a request, returning the response object."""
    print(f"Requesting URL: {url}")
    if params:
        print(f"With params: {params}")
    try:
        response = requests.get(url=url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"Response status: {response.status_code}")
        return response
    except requests.exceptions.Timeout:
        print(f"Request timed out: {url}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return None


def get_lesson_replay_segments(domain, cookie, lesson_id):
    """Get all replay video segments for a given lesson_id."""
    api_url = f'https://{domain}/api/v3/lesson-summary/replay'
    params = {'lesson_id': lesson_id}
    request_headers = {
        'Cookie': cookie,
        'Xtbz': 'ykt',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'https://{domain}/',
    }
    response = launch_request(api_url, params=params, headers=request_headers)
    if not response:
        return f'Lesson_{lesson_id}', []

    segments_to_download = []
    lesson_title_overall = f'Lesson_{lesson_id}'
    try:
        json_data = response.json()
        if json_data.get("code") != 0:
            print(f"API Error for lesson_id {lesson_id}: {json_data.get('msg', 'Unknown error')}")
            return lesson_title_overall, []
        data_payload = json_data.get('data', {})
        lesson_info = data_payload.get('lesson', {})
        lesson_title_overall = sanitize_filename(lesson_info.get('title', f'Lesson_{lesson_id}'))
        live_segments_info = data_payload.get('live', [])
        if not live_segments_info:
            print(f"No 'live' segments for lesson '{lesson_title_overall}'.")
            return lesson_title_overall, []
        for index, seg_info in enumerate(live_segments_info):
            video_url = seg_info.get('url')
            if not video_url:
                print(f"Warning: Seg {index + 1} for '{lesson_title_overall}' no URL. Skipping.")
                continue
            segments_to_download.append({
                'lesson_title': lesson_title_overall,
                'segment_url': video_url,
                'part_number': index + 1,
                'total_parts': len(live_segments_info),
            })
        print(f"Found {len(segments_to_download)} segments for '{lesson_title_overall}'.")
    except ValueError:
        print(f"JSON parse error for {lesson_id}.\nResponse: {response.text[:500]}")
        return lesson_title_overall, []
    except Exception as e:
        print(f"Error processing data for {lesson_id}: {e}")
        return lesson_title_overall, []
    return lesson_title_overall, segments_to_download


def download_video_segment(segment_info, save_dir, domain):
    """Download a single video segment based on the provided segment_info."""
    lesson_title = segment_info['lesson_title']
    segment_url = segment_info['segment_url']
    part_number = segment_info['part_number']
    total_parts = segment_info['total_parts']
    if total_parts > 1:
        segment_filename_base = f"{lesson_title}_Part{part_number}"
    else:
        segment_filename_base = lesson_title
    video_filepath = os.path.join(save_dir, segment_filename_base + ".mp4")
    if os.path.exists(video_filepath):
        print(f"Segment {segment_filename_base}.mp4 exists. Skipping.")
        return video_filepath
    print(f"\nDownloading: {segment_filename_base}.mp4 (Segment {part_number}/{total_parts})")
    print(f"  From URL: {segment_url}")
    try:
        video_response = requests.get(segment_url, stream=True, timeout=120, headers={'Referer': f'https://{domain}/'})
        video_response.raise_for_status()
        total_size = int(video_response.headers.get('content-length', 0))
        downloaded_size = 0
        with open(video_filepath, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress_str = f"\r  Progress: {downloaded_size/1024/1024:.2f}MB"
                    if total_size > 0: progress_str += f" / {total_size/1024/1024:.2f}MB ({(downloaded_size/total_size)*100:.2f}%)"
                    else: progress_str += " (total size unknown)"
                    print(progress_str, end="")
        print(f"\n  Segment {segment_filename_base}.mp4 downloaded.")
        return video_filepath
    except requests.exceptions.Timeout:
        print(f"\n  Timeout: {segment_filename_base}.mp4.")
    except requests.exceptions.RequestException as e:
        print(f"\n  Error downloading {segment_filename_base}.mp4: {e}")
    except IOError as e:
        print(f"\n  Error writing {video_filepath}: {e}")
    return None


def merge_video_parts(video_parts_paths, output_filepath, delete_parts=False):
    """
    Merges video parts using ffmpeg.
    Args:
        video_parts_paths: A list of full paths to video parts, in order.
        output_filepath: The full path for the merged output video.
        delete_parts: Boolean, whether to delete individual parts after successful merge.
    """
    if not video_parts_paths:
        print("No video parts to merge.")
        return False
    if len(video_parts_paths) == 1:
        print("One part found. Renaming to final output name if different.")
        if video_parts_paths[0] != output_filepath:
            try:
                if os.path.exists(output_filepath):
                    print(f"Warning: Output {output_filepath} exists. Skipping rename.")
                else:
                    os.rename(video_parts_paths[0], output_filepath)
                    print(f"Renamed '{video_parts_paths[0]}' to '{output_filepath}'.")
            except OSError as e:
                print(f"Error renaming single part: {e}")
        return True
    print(f"\nMerging {len(video_parts_paths)} parts into '{os.path.basename(output_filepath)}'...")
    list_filepath = os.path.join(os.path.dirname(output_filepath), "ffmpeg_list.txt")
    with open(list_filepath, 'w', encoding='utf-8') as f:
        for part_path in video_parts_paths:
            f.write(f"file '{os.path.abspath(part_path)}'\n")
    ffmpeg_command = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_filepath, '-c', 'copy', output_filepath]
    try:
        print(f"Executing: {' '.join(ffmpeg_command)}")
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            print("Merge successful.")
            if delete_parts:
                print("Deleting parts...")
                for part_path in video_parts_paths:
                    try:
                        os.remove(part_path)
                        print(f"  Deleted: {os.path.basename(part_path)}")
                    except OSError as e:
                        print(f"  Error deleting {os.path.basename(part_path)}: {e}")
            return True
        else:
            print("Error during ffmpeg merging process.")
            print("ffmpeg stdout:")
            print(stdout.decode(errors='ignore'))
            print("ffmpeg stderr:")
            print(stderr.decode(errors='ignore'))
            return False
    except FileNotFoundError:
        print("Error: ffmpeg not found. Ensure it's installed and in PATH.")
    except Exception as e:
        print(f"Unexpected merge error: {e}")
    finally:
        if os.path.exists(list_filepath):
            os.remove(list_filepath)
    return False


def download_lesson(domain, cookie, lesson_id, save_directory, delete_parts_after_merge=True, lesson_title_hint=None):
    """
    Downloads all segments for a single lesson_id, merges them, and saves.
    Returns True if successful, False otherwise.
    """
    print(f"\n--- Starting processing for Lesson ID: {lesson_id} ---")

    lesson_title, replay_segments_info = get_lesson_replay_segments(domain, cookie, lesson_id)
    if lesson_title_hint and lesson_title_hint != lesson_title:
        print(f"Lesson title mismatch! Expected: {lesson_title_hint}, Found: {lesson_title}")
        return False

    if not replay_segments_info:
        print(f"Failed to retrieve replay segments for LessonID: {lesson_id} (Title: '{lesson_title}')")
        return False

    if not os.path.exists(save_directory):
        try:
            os.makedirs(save_directory)
            print(f"Created directory: {save_directory}")
        except OSError as e:
            print(f"Creating directory {save_directory} failed: {e}")
            return False

    merged_video_filename = f"{lesson_title}.mp4"
    merged_video_filepath = os.path.join(save_directory, merged_video_filename)
    if os.path.exists(merged_video_filepath):
        print(f"File '{merged_video_filename}' already exists in '{save_directory}'. Skipping download.")
        return True

    print(f"\nPreparing to download {len(replay_segments_info)} video segments for lesson '{lesson_title}' into folder '{save_directory}'.")

    downloaded_parts_paths = []
    all_downloads_successful = True
    for i, segment_info in enumerate(replay_segments_info):
        print(f"\n--- Processing segment {i+1} / {len(replay_segments_info)} for '{lesson_title}' ---")
        assert segment_info['lesson_title'] == lesson_title, "Segment title mismatch!"
        downloaded_path = download_video_segment(segment_info, save_directory, domain)
        if downloaded_path:
            downloaded_parts_paths.append(downloaded_path)
        else:
            all_downloads_successful = False
            break
        if i < len(replay_segments_info) - 1:
            time.sleep(1)

    if all_downloads_successful and downloaded_parts_paths:
        print(f"\nAll video segments for lesson '{lesson_title}' have been successfully downloaded or already exist.")

        if len(downloaded_parts_paths) > 0:


            merge_success = merge_video_parts(
                downloaded_parts_paths,
                merged_video_filepath,
                delete_parts_after_merge
            )
            if merge_success:
                print(f"Lesson '{lesson_title}' (ID: {lesson_id}) successfully processed and merged to '{merged_video_filepath}'.")
                return True
            else:
                print(f"Merging failed for lesson '{lesson_title}' (ID: {lesson_id}). Parts are kept.")
                return False
        else:
            print("No parts were downloaded for this lesson, skipping merge.")
            return True
    elif not downloaded_parts_paths and not replay_segments_info:
        print(f"\nNo video segments found to download for lesson '{lesson_title}' (ID: {lesson_id}).")
        return True
    else:
        print(f"\nSome segments for lesson '{lesson_title}' (ID: {lesson_id}) failed. Merging skipped.")
        return False


if __name__ == '__main__':

        config = {
            'SaveDirName': 'test',
            'Cookie': 'YOUR_COOKIE_HERE',
            'LessonID': '906908668424168576',
            'DeletePartsAfterMerge': True,
            'MaxRetries': 3,
        }

        success = False
        for attempt in range(config['MaxRetries']):
            print(f"\nAttempt {attempt + 1}/{config['MaxRetries']} for lesson ID: {config['LessonID']}")
            success = download_lesson(
                domain=DOMAIN,
                lesson_id=config['LessonID'],
                cookie=config['Cookie'],
                save_directory=os.path.join(DOWNLOAD_BASE_DIR, config['SaveDirName']),
                delete_parts_after_merge=config['DeletePartsAfterMerge']
            )
            if success:
                print(f"Lesson (ID: {config['LessonID']}) processed successfully on attempt {attempt + 1}.")
                break
            else:
                if attempt < config['MaxRetries'] - 1:
                    print(f"Attempt {attempt + 1} failed. Retrying...")
                    time.sleep(2)  # Wait before retry
                else:
                    print(f"All {config['MaxRetries']} attempts failed for lesson (ID: {config['LessonID']}).")

