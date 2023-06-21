from loguru import logger
import os
import re
import glob
import shutil
import subprocess
import ffmpeg

class VideoUtils:
    def __init__(self, timelapse_dir, name):
        self.timelapse_dir = timelapse_dir
        self.name = name

        import shutil

    def generate_video_from_photos(self, image_file_paths, video_name_counter):
        def sort_key(file_path):
            match = re.search(r"\d+(?=\.[a-z]+)", file_path)
            return int(match.group()) if match else 0

        capture_parent_dir = os.path.join(self.timelapse_dir, self.name)
        file_output_name = self.name
        temp_output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}_temp.mp4")
        final_output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}_final.mp4")
        output_path = os.path.join(capture_parent_dir, 'output', f"{file_output_name}{video_name_counter}.mp4")

        sorted_files = sorted((i for i in image_file_paths if isinstance(i, str)), key=sort_key)
        with open(f"/tmp/file_list{video_name_counter}.txt", "w") as f:
            for file in sorted_files:
                f.write(f"file '{file}'\n")

        # files_str = '|'.join(sorted_files)
        logger.info(f"files string list: {str(sorted_files)}")
        # command = f"ffmpeg -pattern_type glob -i 'concat:{files_str}' -filter:v 'deflicker=mode=pm:size=10,scale=size=3840x2160:force_original_aspect_ratio=increase' -c:v libx264 -crf 20 -preset slow -movflags faststart -pix_fmt yuv420p {output_path}"


        # Use the file list as input for ffmpeg
        logger.info("Concatenating files into timelapse and applying filters with ffmpeg")
        (
            ffmpeg
            .input(f"/tmp/file_list{video_name_counter}.txt", format="concat", safe=0)
            .filter('deflicker', mode='pm', size=10)
            .filter('scale', size='3840x2160', force_original_aspect_ratio='increase')
            .output(f'{output_path}', crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
            .run(overwrite_output=True)
        )

        video_files = sorted(glob.glob(os.path.join(capture_parent_dir, 'output', f"{file_output_name}*.mp4")), key=sort_key)

        logger.info(f"video files list: {str(video_files)}")

        if video_files:
            inputs = [ffmpeg.input(video) for video in video_files]

            try:
                (
                    ffmpeg
                    .concat(*inputs, v=1, a=0)
                    .output(temp_output_path, crf=20, preset='slow', movflags='faststart', pix_fmt='yuv420p')
                    .run(overwrite_output=True)
                )
                for video in video_files:
                    os.remove(video)
                shutil.move(temp_output_path, final_output_path)
            except Exception as e:
                logger.error(f"Error concatenating videos or removing old videos: {e}")
                return None

            logger.info(f"Current video size is {os.path.getsize(final_output_path)} bytes")

            return final_output_path
