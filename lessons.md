# CET-6 日常踩坑记录

## 2026-05-24

### 技术坑
1. **模板注释误匹配**：cet6-template.html 注释里写了 "const DATA = {...}" 作为说明文字。字符串替换匹配到了注释里的文字而非 `<script>` 内的实际声明，导致 <!DOCTYPE>/<head>/<body> 全部被删。修复：用 `// ========== DATA ==========` 锚点定位，再找后面的 `var DATA = {`。

2. **音频选项挤一行**：`A.xxx  B.xxx  C.xxx  D.xxx` 全挤一行，edge-tts 当成一句糊读。修复：每选项独立一行 `A.xxx\nB.xxx\nC.xxx\nD.xxx`。

3. **JS覆盖静态HTML**：修改了静态HTML中听力题干为 `class="quest-label"`，但页面加载时 JS 的 `renderQuestions()` 又写回完整题干。修复：修改 JS，听力 section 只输出题号不输出题干文本。

4. **execute_code 的 read_file 不可靠**：返回 `{"content_returned": bool|str}`，不如直接用终端 Python heredoc。

5. **topic_log 被覆盖**：execute_code 读写导致旧数据丢失。改用 write_file 直接覆盖全量。

6. **github.io 域名 GFW 阻断**：和 github.com 一样需要 Watt Toolkit。

### 质量坑
7. **题文同序标注**：[Q1]...[Q5] 原文插入每次必忘。
8. **选项长度超限**：passage 有9词选项，lecture 有9词选项（听力上限8词）。
9. **阅读题型不足**：tech/social 只有主旨+细节2种，需要≥3种。
10. **翻译中文超限**：202字，目标180-200。
11. **作文严重套模板**：AI高频句式"has sparked debate" "On the one hand/other hand" "lies not in but in"，阅卷老师一眼认出。
12. **未做重叠率检查**：正确项-原文 difflib 重叠率检查完全跳过。
13. **干扰项未逐题核查**："只改一个点"原则没有逐题验证。

### 质量标准
- 用户要求优(≥95)或良(≥88)，及格线不发布
- 生成后必须逐项自检打分，单项<20重做
- v3评分：听力25+阅读25+翻译25+作文25=100
