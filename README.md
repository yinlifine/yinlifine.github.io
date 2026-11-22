# 2027 教育学博士招生追踪网站（GitHub Actions 自动发布版）

此项目面向15所国内高校的2027年教育学相关全日制学术学位博士招生，初始人工核实日期为2026-11-22。适用于已经建立好个人 GitHub Pages 仓库 `yinlifine.github.io` 的情况。

## 一、最简单的首次安装（原有主页网址不变）

1. 解压下载的部署 ZIP，打开解压后的文件夹。注意上传**文件夹里面的内容**，不是 ZIP，也不要在仓库根目录多套一层项目文件夹。
2. 登录 https://github.com/yinlifine/yinlifine.github.io ，在 `Code` 页面确认分支为 `main`，点击 `Add file → Upload files`。
3. 把解压目录中的以下项目**一起拖入网页上传区域**：`.github`、`data`、`docs`、`scripts`、`site`、`requirements.txt`、`README.md`。确认上传文件名保留目录层级，例如 `.github/workflows/monitor.yml`、`docs/index.html`、`data/schools.json`。你原来的仓库根目录 `index.html` **不用删除**，之后不再作为发布源。
4. 选择直接提交到 `main`，点击 `Commit changes`。上传整个文件夹的能力取决于浏览器与 GitHub 网页行为；若不保留目录，**不要提交错误结构**，改用 GitHub Desktop 或 github.dev 上传，并保持上述相对路径。
5. 进入 `Settings → Pages → Build and deployment`，把 `Source` 从 `Deploy from a branch` 改成 **`GitHub Actions`**。这一步很重要：旧版的分支发布模式不会因 `GITHUB_TOKEN` 所提交的更新自动重新构建。
6. 进入 `Settings → Actions → General → Workflow permissions`，确认 `Read and write permissions` 可选且已勾选，点击 `Save`。仓库的分支保护规则也不能禁止该工作流对 `main` 提交。
7. 进入仓库 `Actions`，左侧找到 `Check official doctoral admissions pages`，点击 `Run workflow`，选择 `main`，再点绿色 `Run workflow`。首次运行会建立对比基准；后续计划每6小时运行一次。
8. 工作流页面显示绿色对勾后，打开 https://yinlifine.github.io/ 。在页面“官网自动监测记录”区域应能看到“最近自动检查时间”；若有学校官网访问限制，可能显示失败项，此时不是“没有新公告”。

如果网页上传器无法保留文件夹路径，可以使用 [github.dev 浏览器编辑器](https://github.dev/yinlifine/yinlifine.github.io) 在左侧文件树中拖入这些文件夹，完成后在左侧 `Source Control` 点击 `Commit & Push`（它可能要求你确认或授权）。

## 二、网站是什么样的更新机制？

- GitHub Actions 执行 `scripts/check_sources.py`，尝试读取 `data/schools.json` 中的 `monitorUrls` 官方网站列表，并与上次记录比较。
- 网页文本发生变化或有新的匹配公告链接时，写入 `docs/data/monitor.json`，**只标注“自动发现，待核实”**。
- Actions 调用 `scripts/build_site.py`，依据人工确认的 `data/schools.json` 重新生成 `docs/index.html`，然后使用 `actions/deploy-pages` 直接发布 `docs` 目录。
- 本次修正版的 `Settings → Pages → Source` 必须选 **GitHub Actions**，而不是 `main/(root)` 或 `main/docs`。
- 自动监测不会从网页直接推断报名截止时间、专业名额和导师名额，更不会自动覆盖已核实信息；确认后要在 `data/schools.json` 中更新字段并提交，提交会自动触发重新生成和部署。

## 三、文件说明

```text
.github/workflows/monitor.yml  定时检查 + 自动发布工作流
data/schools.json           15所高校经过人工核实的基础数据
scripts/check_sources.py    官网变化检测，结果仅作为待核实线索
scripts/build_site.py       重新生成网站
site/template.html          网页模板
docs/index.html             网站入口（自动生成）
docs/data/monitor.json      监测结果日志
requirements.txt            Python依赖
```

仓库根目录原来的 `index.html` 可以保留，不会影响 Github Actions 从 `docs/` 部署。原始部署包中的 `scripts/test_offline.py` 是离线模拟测试；无需日常操作。

## 四、时间与局限

- GitHub 的 cron 使用 UTC。`17 */6 * * *` 对应北京时间每天 **02:17、08:17、14:17、20:17** 的计划检查。并非整点实时；工作流可能延迟甚至漏跑。
- 学校网页可能要求验证码、使用动态加载、跳转或临时拒绝访问。抓取失败不等于没有招生公告。
- 某些公告以附件 PDF 或图片发布，本程序不保证提取其内容；以官方原文为最终依据。
- GitHub Pages 是公开网站，不要把任何私人申请资料或密码写入公共仓库。
- 这是**自动网页变化监测系统**而非完全自动审核、自动补全所有招生字段的数据库。已核实字段需人工确认并更新 `data/schools.json`。
