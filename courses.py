import os
import time
import requests
import lessons

DOMAIN = 'pro.yuketang.cn'
DOWNLOAD_BASE_DIR = '/mnt/wsl/hdd/RainDownload'


def get_all_lessons_for_classroom(domain, cookie, classroom_id, page_size, activity_type=None, reverse_order=True):
    """Get all lesson information (LessonID and title) for a specified classroom, handling pagination."""
    all_lessons_info = []
    current_page = 0

    print(f"\nFetching lesson list for ClassroomID: {classroom_id}")

    request_headers = {
        'Cookie': cookie,
        'Xtbz': 'ykt',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'https://{domain}/v2/web/studentLog/{classroom_id}',
    }

    while True:
        api_url = f'https://{domain}/v2/api/web/logs/learn/{classroom_id}'
        params = {
            'actype': -1,
            'page': current_page,
            'offset': page_size,
            'sort': -1
        }

        print(f"  Fetching page {current_page} (offset {page_size})...")

        try:
            response = requests.get(api_url, params=params, headers=request_headers, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if json_data.get("errcode") != 0:
                print(f"  API Error on page {current_page}: {json_data.get('errmsg', 'Unknown error')}")
                break

            data_payload = json_data.get('data', {})
            activities = data_payload.get('activities', [])
            if not activities:
                print(f"  No more activities found on page {current_page}. Reached end of list.")
                break

            page_lessons_found = 0
            for activity_item in activities:
                lesson_id = activity_item.get('courseware_id')
                title = activity_item.get('title')
                activity = activity_item.get('type')
                if lesson_id and title:
                    if activity_type is None or activity == activity_type:
                        all_lessons_info.append({
                            'lesson_id': str(lesson_id),
                            'title': lessons.sanitize_filename(title)
                        })
                        page_lessons_found += 1
                    else:
                        print(f"    Skipping '{title}' (ID: {lesson_id}) due to type: {activity} (Expected: {activity_type}).")
                else:
                    print(f"    Warning: Could not extract courseware_id or title from item: {activity_item}")
            print(f"  Found {page_lessons_found} usable lessons on page {current_page}.")
            if len(activities) < page_size:
                print(f"  Fetched {len(activities)} items, which is less than offset {page_size}. Assuming end of list.")
                break

            current_page += 1
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"  Request failed for page {current_page}: {e}")
            break
        except ValueError:
            print(f"  Failed to parse JSON response for page {current_page}.")
            if 'response' in locals():
                print("  Response content:", response.text[:500])
            break
        except Exception as e:
            print(f"  An unexpected error occurred while fetching page {current_page}: {e}")
            break

    if all_lessons_info and reverse_order:
        all_lessons_info.reverse()
        print("Reversed lesson list to process oldest first.")

    print(f"Total usable lessons found across all pages: {len(all_lessons_info)}.")
    return all_lessons_info


if __name__ == '__main__':

    config = {
        'SaveDirName': 'cwj_计算机程序设计基础',
        'Cookie': 'YOUR_COOKIE_HERE',
        'ClassroomID': '3054346',
        'DeletePartsAfterMerge': True,
        'ActivityTypeToDownload': 14, # 14 for video lessons, None to download all types
        'PageSize': 20,
        'reverseOrder': True, # True to process oldest lessons first
        'MaxRetries': 3, # Maximum number of retries for failed downloads
    }

    print("--- Yuketang Course Downloader ---")

    save_dir = os.path.join(DOWNLOAD_BASE_DIR, config['SaveDirName'])

    all_lessons = get_all_lessons_for_classroom(
        domain=DOMAIN,
        cookie=config['Cookie'],
        classroom_id=config['ClassroomID'],
        page_size=config['PageSize'],
        activity_type=config['ActivityTypeToDownload'],
        reverse_order=config['reverseOrder']
    )

    if not all_lessons:
        print(f"No lessons found or error fetching lessons for ClassroomID {config['ClassroomID']}. Exiting.")
        exit(1)

    total_lessons = len(all_lessons)
    print(f"\nFound {total_lessons} lessons to process for ClassroomID {config['ClassroomID']}.")

    overall_success_count = 0
    overall_failure_count = 0

    for index, lesson_data in enumerate(all_lessons):
        lesson_id = lesson_data['lesson_id']
        lesson_title = lesson_data['title']

        print(f"\n======================================================================")
        print(f"Processing Lesson {index + 1}/{total_lessons}: '{lesson_title}' (ID: {lesson_id})")
        print(f"======================================================================")

        success = False
        retry_count = 0
        max_retries = config['MaxRetries']

        while not success and retry_count <= max_retries:
            if retry_count > 0:
                print(f"Retry attempt {retry_count}/{max_retries} for lesson '{lesson_title}' (ID: {lesson_id})")
                time.sleep(5)  # Wait before retry

            success = lessons.download_lesson(
                domain=DOMAIN,
                lesson_id=lesson_id,
                cookie=config['Cookie'],
                save_directory=save_dir,
                delete_parts_after_merge=config['DeletePartsAfterMerge'],
                lesson_title_hint=lesson_title,
            )

            retry_count += 1

        if success:
            overall_success_count += 1
            print(f"--- Successfully processed lesson '{lesson_title}' (ID: {lesson_id}) ---")
        else:
            overall_failure_count += 1
            print(f"--- Failed to process lesson '{lesson_title}' (ID: {lesson_id}) after {max_retries} retries ---")

        if index < total_lessons - 1:
            time.sleep(3)

    print("\n\n--- Course Download Summary ---")
    print(f"Total lessons attempted: {total_lessons}")
    print(f"Successfully processed: {overall_success_count}")
    print(f"Failed to process: {overall_failure_count}")
    print(f"All downloaded videos are in subdirectories under: {os.path.abspath(config['SaveDirName'])}")
    print("--- All tasks complete. ---")
