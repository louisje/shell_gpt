# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0.post1] - 2026-01-28

### Changed
- 合併上游 1.5.0 版本
  - 遷移至 OpenAI v2 SDK（`openai >= 2.0.0`）
  - 改進 tool_call 處理，新增 LiteLLM 相容性
  - 確保第一條聊天訊息被保留，避免 "Could not determine chat role" 錯誤
  - 在回應 chunks 中檢查空 choices
  - LLM 函數優化

### Fixed
- 修正 OpenAI v2 API 相容性問題（assistant message content 改為 `None`）

## [1.4.5.post4] - 2026-01-21

### Added
- 新增 `--show-chat last` 功能，顯示最近使用的 chat session 內容
- 新增 Chat ID 自動補全功能
  - `--chat`, `--repl`, `--show-chat` 選項支援 Tab 補全
  - 補全選項包含 `last`, `temp`, `auto` 特殊關鍵字及所有現有 chat session
- 新增 `--install-completion` 安裝 shell 補全腳本
  - Bash: 安裝到 `~/.bash_completion.d/sgpt-completion.sh`
  - Zsh: 安裝到 `~/.zfunc/_sgpt`
  - Fish: 安裝到 `~/.config/fish/completions/sgpt.fish`
- 新增 `--install-integration` 安裝 shell 整合腳本到 `~/.bash_profile.d/sgpt.sh`

### Changed
- 美化 `--show-chat` 輸出，使用 Rich Panel 邊框樣式
  - 標題格式改為 `[ Title Case ]`（底線轉空格，首字母大寫）
  - 用戶訊息顯示為 cyan 色
  - 系統訊息顯示為 green 色
- 美化 `--list-chats` 輸出
  - 使用 Rich Panel 邊框樣式
  - 顯示每個 chat session 的最後修改時間戳

### Fixed
- 修復自動補全機制（在 `add_completion=False` 時正確處理補全請求）
- 修復因代碼行為變更導致的測試失敗
  - 新增 `CompletionMock` 類別解決 mock 引用問題
  - 更新 `comp_args()` 從配置讀取 temperature 和 max_tokens
- 隔離測試環境，避免載入用戶自定義函數

## [1.4.5.post3] - 2026-01-15

### Added
- 新增 `--chat auto` 功能，讓 AI 自動根據對話內容生成聊天名稱
  - 對話完成後會呼叫 AI 生成一個簡短的描述性名稱（2-5 個英文單字）
  - 名稱僅使用小寫字母、數字和連字號，最長 50 字元
  - 如果名稱已存在，會自動添加數字後綴（如 `python-help-2`）
  - 完成後顯示：`Chat session created: <名稱>`
- 新增 `--chat last` 功能，快速恢復最後一次對話
  - 與 `--resume` 功能相同，但使用 `--chat` 語法
  - 提供更一致的 `--chat` 選項體驗

### Changed
- 更新 `--chat` 選項說明，包含 `auto` 和 `last` 的特殊用法

## [1.4.5.post2] - 2026-01-15

### Fixed
- 修復 shell 集成（Ctrl-S）與 default 聊天角色衝突的問題
  - `--shell`、`--code`、`--describe-shell` 模式現在預設使用單次對話（DefaultHandler）
  - 只有明確使用 `--chat` 選項時，這些模式才會啟用持久對話
  - 每次啟動預設對話時會清除舊的 default 聊天記錄（除非使用 `--resume` 或明確指定 `--chat`）

### Changed
- 改進 `--chat temp` 的行為
  - temp 對話現在在連續使用時會保持狀態
  - 只有切換到其他對話 ID 時才會清除 temp 對話
  - 添加了最後使用的聊天 ID 追踪功能

## [1.4.5.post1] - 2026-01-13

### Added
- 新增 `--resume` 選項（簡寫 `-r`）來恢復最後使用的對話 session
  - 如果沒有任何 chat session，則會創建一個新的 "default" session
  - 顯示恢復的 session 名稱，提供更好的用戶體驗

### Changed
- **重要變更**：預設行為現在會自動將對話保存到 "default" session
  - 即使不使用 `--chat` 選項，對話歷史也會被保存
  - 每次不帶 `--chat` 參數的呼叫都會累積在 "default" session 中
  - 這使得對話管理更加直觀和自動化

### Fixed
- 添加了 `--resume` 和 `--chat` 選項的互斥檢查，避免同時使用導致的混淆

## [Unreleased]

### Added
- Shell 集成快捷鍵檢查：添加交互式終端檢查

### Changed
- 將 shell 集成快捷鍵從 Ctrl-B 改為 Ctrl-S
- 重構：將 OPENAI_* 環境變數重命名為 TWCC_*
- 統一 API_BASE_URL 環境變數名稱為 TWCC_API_BASE

### Fixed
- 修復失敗的單元測試 (#733)

## [1.4.5] - 2025-04-08

### Added
- 新增 LiteLLM 管理 API keys 的選項 (#604)
- 添加完整的 Makefile 及更新 shell 集成 (d6046b9)

### Changed
- 更新 Python 版本要求和相關依賴 (#671)
- 移除 openai、rich 和 instructor 的版本上限限制
- 在緩存檔案中保留 system role 訊息

### Fixed
- 修復訊息緩存長度問題 (#683)
- 在 chat 訊息緩存中保留 system message (#669)
- 修復 --show-chat 和 --repl 遵守 --no-md 選項 (#513)
- 修復 Python 3.12 中移除的 unittest.mock assertion (#554)
- 修復空 choices[] 問題
- 修復 max_tokens 處理
- CD pipeline 修復 (#608)

## [1.4.4] - 2024-11-XX

### Added
- 為生成的 shell 命令實作 modify 選項 (#566)
- 採用支援 Groq 和其他模型的新函數呼叫機制 (#569)

### Changed
- 將預設模型更新為 gpt-4o (#580)
- Docker container 改進 (#540)

### Fixed
- 修復 shell 識別問題 (#544)
- Shell 命令修改的次要測試修復
- 次要 lint 修復
- 次要錯誤修復和文件更新 (#607)
- Docker image release action 修復
- 修復 release action 中的版本問題

## [1.4.2] - 2024-XX-XX

### Fixed
- 修復 release action 中的版本問題 (#536)

## [1.4.1] - 2024-XX-XX

### Added
- PyPI 和 GitHub release actions (#535)

### Fixed
- 修復函數呼叫後的 chat 和 REPL 模式輸出 (#525)
- 修復串流時的鍵盤中斷處理 (#521)
- 在第一個等號處分割配置行 (#504)

## [1.4.0] - 2023-XX-XX

### Added
- Azure 整合 Wiki 頁面 (#491)
- Ollama 整合 🦙 (#463)
- OpenAI 函數呼叫 (#427)
- OpenAI SDK 依賴 (#414)
- 新的配置變數 API_BASE_URL (#477)
- Markdown 選項和配置變數 (#481)
- Chat 歷史的 Markdown 格式化 (#444)

### Changed
- 預設使用 OpenAI，將 LiteLLM 設為選用 (#488)
- 主要重構和優化 (#462)
- --shell 的非互動模式和集成變更 (#455)
- 改進的測試，REPL stdin，文件更新 (#452)
- 使用模擬 API 回應改進測試 (#442)

### Fixed
- 次要錯誤修復和 API_BASE_URL 相關問題 (#477)
- 修復 stdin 和 --shell 選項的問題 (#439)

## [1.0.1] - 2023-XX-XX

### Fixed
- REPL 對話錯誤修復和次要改進 (#410)

## [1.0.0] - 2023-XX-XX

### Added
- 顯示 sgpt 版本的命令列選項 (#394)
- REPL 中的多行輸入 (#393)
- 選項以停用回應串流 (#290)
- 使用 LocalAI 運行 sgpt 的選項 (#307)
- GitHub Codespaces 設定 (#65)

### Changed
- 為預設輸出渲染 markdown (#400)
- GPT4+ 模型的 system role 優化 (#398)
- System role 的次要改進 (#402)
- REPL 多行文件和改進 (#401)
- 改進 chat 模式和 REPL 模式的文件 (#284)

### Fixed
- 修復配置檔案空行崩潰問題 (#386)
- 修復 Dockerfile 中的 home directory 問題 (#382)
- 處理 API 認證回應 (#395)
- README.md 中的次要 shell 命令範例修復 (#280)

## [0.9.3] - 2023-XX-XX

### Added
- 新增 GPT 模型 (#263)
- 簡單的 shell 整合 (#267)
- 執行時描述 --shell 命令的選項 (#249)
- 描述 shell 命令選項 (#195)
- .sgptrc 配置檔案中的註解過濾 (#226)
- 預設執行 shell 命令的配置參數 (#246)
- 自訂 roles (#183)
- Codespell 檢查和 workflow (#287)

### Changed
- 更新預設溫度範圍 (#223)
- 遷移到 TOML，新的 linting 和更嚴格的 typing (#165)

### Fixed
- 隱藏 Rich tracebacks 中的 API key (#221)
- README.md 中的拼寫錯誤修復 (#115)

### Removed
- 移除日期限制的模型 (#285)

## [0.9.0] - 2023-XX-XX

### Added
- 從 stdin 接受提示 (#163)
- 更改 completion 顏色的選項 (#157)
- 支援 GPT-4 的模型選擇選項 (#151)
- Chat sessions 的 REPL 模式 (#94)

### Changed
- 原生 $SHELL 命令和更好的 Windows 支援 (#149)

### Fixed
- 修復 shell 命令輸出串流 (#150)
- 修復 chat messages 和 prompt 的錯誤

## [0.7.0] - 2023-XX-XX

### Added
- Chat 模式
- Caching 功能
- 即時串流
- Prompt engineering

### Changed
- 程式碼和檔案結構改進
- 重構、更多測試、lint 修復、優化

### Fixed
- GitHub action 修復

## [0.6.0] - 2023-XX-XX

### Added
- ChatGPT 實作
- PowerShell 支援
- Unittests
- GitHub action
- Dockerfile
- Docker volume 用於 cache 持久化
- OPENAI_API_KEY 環境變數
- OS 識別

### Changed
- 更準確的回應
- Prompt 改進

### Fixed
- 自動二進位 releases 的 action
- API key 提示的錯誤修復

## [0.4.0] - 2023-XX-XX

### Added
- --shell --execute 的快捷鍵
- 彩色輸出
- Linting GitHub workflow
- Pre-push hook

### Changed
- 次要優化

### Fixed
- 在發送到 openai 前不轉義 prompt

## [0.1.0] - 2023-XX-XX

### Added
- 初始版本
- 基本 OpenAI API 整合
- 命令列介面
- MIT 授權
