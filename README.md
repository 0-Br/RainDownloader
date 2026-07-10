# RainDownloader

**从[荷塘雨课堂](https://pro.yuketang.cn)批量下载课程回放视频的命令行工具**

荷塘雨课堂（Yuketang）是清华大学广泛使用的在线教学平台，支持课堂直播与回放。本工具通过其 API 接口自动获取课程列表并下载回放视频，适用于需要离线保存课程录像的场景。

## 功能

- 自动获取指定课堂的全部课程列表，支持分页遍历
- 下载课程回放视频，支持多分段视频的自动合并
- 使用 ffmpeg 拼接多段视频为完整文件
- 断点续传：已下载的文件自动跳过
- 失败自动重试

## 依赖

- Python 3
- [requests](https://pypi.org/project/requests/)
- [ffmpeg](https://ffmpeg.org/)（用于合并多分段视频，需加入系统 PATH）

## 使用方法

1. 登录[荷塘雨课堂](https://pro.yuketang.cn)，从浏览器开发者工具中获取登录 Cookie
2. 编辑 `courses.py`：
   - `DOWNLOAD_BASE_DIR`（文件头部）：下载根目录，默认值为 WSL 专属路径
   - `Cookie`（底部配置区）：填入登录 Cookie
   - `ClassroomID`（底部配置区）：目标课堂 ID
   - `SaveDirName`（底部配置区）：视频保存子目录名
3. 运行批量下载：
   ```bash
   python courses.py
   ```

也可使用 `lessons.py` 单独下载指定课程（编辑底部 `LessonID`）：
```bash
python lessons.py
```

## 配置项

| 变量 | 位置 | 说明 |
|------|------|------|
| `DOWNLOAD_BASE_DIR` | 文件头部 | 下载文件的根目录（默认 `/mnt/wsl/hdd/RainDownload`，非 WSL 环境需修改） |
| `DOMAIN` | 文件头部 | 雨课堂域名（默认 `pro.yuketang.cn`） |
| `Cookie` | 入口配置 | 登录会话 Cookie |
| `ClassroomID` | `courses.py` | 目标课堂 ID |
| `SaveDirName` | 入口配置 | 视频保存子目录名 |
| `DeletePartsAfterMerge` | 入口配置 | 合并后是否删除分段文件 |
| `ActivityTypeToDownload` | `courses.py` | 活动类型筛选（`14` = 视频课） |

## 项目结构

| 文件 | 用途 |
|------|------|
| `courses.py` | 批量下载入口：获取课堂的全部课程列表，逐一调用下载逻辑 |
| `lessons.py` | 单课程下载：视频分段获取、下载、ffmpeg 合并的核心实现 |

## 声明

本项目仅供学习交流参考。使用者应确保对所下载内容拥有合法访问权限，并遵守相关平台的服务条款。
