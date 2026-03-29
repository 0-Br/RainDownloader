# RainDownloader

从[荷塘雨课堂](https://pro.yuketang.cn)（Yuketang）下载课程回放视频的脚本。

## 功能

- 自动获取课堂的所有课程列表（支持分页）
- 下载课程回放视频（支持多分段视频）
- 使用 ffmpeg 自动合并多分段视频
- 支持断点续传（已下载的文件自动跳过）
- 支持失败自动重试

## 依赖

- Python 3
- [requests](https://pypi.org/project/requests/)
- [ffmpeg](https://ffmpeg.org/)（用于合并多分段视频）

## 使用方法

1. 登录[荷塘雨课堂](https://pro.yuketang.cn)，从浏览器开发者工具中获取你的 Cookie
2. 编辑 `courses.py` 底部的配置：
   - `Cookie`：填入你的 Cookie
   - `ClassroomID`：目标课堂 ID
   - `SaveDirName`：保存目录名（将在 `DOWNLOAD_BASE_DIR` 下创建）
3. 运行：
   ```bash
   python courses.py
   ```

也可以使用 `lessons.py` 单独下载指定课程（编辑底部的 `LessonID`）：
```bash
python lessons.py
```

## 配置说明

| 变量 | 位置 | 说明 |
|------|------|------|
| `DOWNLOAD_BASE_DIR` | 文件顶部 | 下载文件的基础存储路径 |
| `DOMAIN` | 文件顶部 | 雨课堂域名 |
| `Cookie` | `__main__` 配置 | 你的登录 Cookie |
| `ClassroomID` | `courses.py` 配置 | 目标课堂 ID |
| `SaveDirName` | 配置 | 课程保存子目录名 |
| `DeletePartsAfterMerge` | 配置 | 合并后是否删除分段文件 |
| `ActivityTypeToDownload` | `courses.py` 配置 | 活动类型筛选（14 = 视频课） |

## 文件说明

- `courses.py` — 批量下载整个课堂的所有课程视频
- `lessons.py` — 下载单个课程的视频，包含视频下载与合并的核心逻辑
