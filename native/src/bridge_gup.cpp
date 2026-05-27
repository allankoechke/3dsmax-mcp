#include "mcp_bridge/bridge_gup.h"
#include "mcp_bridge/chat_ui.h"
#include "mcp_bridge/llm_client.h"
#include "mcp_bridge/handler_helpers.h"
#include <maxapi.h>
#include <notify.h>
#include <shlobj.h>
#include <fstream>
#include <sstream>
#include <string>

// ── ClassDesc2 ──────────────────────────────────────────────────
class MCPBridgeClassDesc : public ClassDesc2 {
public:
    int IsPublic() override { return TRUE; }
    void* Create(BOOL) override { return new MCPBridgeGUP(); }
    const TCHAR* ClassName() override { return _T("MCP Bridge"); }
    const TCHAR* NonLocalizedClassName() override { return _T("MCP Bridge"); }
    SClass_ID SuperClassID() override { return GUP_CLASS_ID; }
    Class_ID ClassID() override { return MCP_BRIDGE_CLASS_ID; }
    const TCHAR* Category() override { return _T("MCP"); }
    const TCHAR* InternalName() override { return _T("MCPBridge"); }
    HINSTANCE HInstance() override { return hInstance; }
};

static MCPBridgeClassDesc mcpBridgeDesc;
ClassDesc2* GetMCPBridgeDesc() { return &mcpBridgeDesc; }

// ── Register macroscripts after Max is fully loaded ─────────────
static MCPBridgeGUP* g_gupInstance = nullptr;

static std::string LocalAppDataDir() {
    char buf[MAX_PATH];
    if (FAILED(SHGetFolderPathA(nullptr, CSIDL_LOCAL_APPDATA, nullptr, 0, buf))) {
        return {};
    }
    return std::string(buf) + "\\3dsmax-mcp";
}

static std::string InstancesDir() {
    auto dir = LocalAppDataDir();
    return dir.empty() ? "" : (dir + "\\instances");
}

static std::string ActiveInstancePath() {
    auto dir = LocalAppDataDir();
    return dir.empty() ? "" : (dir + "\\active_instance.json");
}

static std::string InstancePath(const std::string& instance_id) {
    auto dir = InstancesDir();
    return dir.empty() ? "" : (dir + "\\" + instance_id + ".json");
}

static void EnsureRegistryDirs() {
    std::string base = LocalAppDataDir();
    std::string instances = InstancesDir();
    if (!base.empty()) CreateDirectoryA(base.c_str(), nullptr);
    if (!instances.empty()) CreateDirectoryA(instances.c_str(), nullptr);
}

static std::string JsonEscape(const std::string& value) {
    std::string out;
    out.reserve(value.size() + 8);
    for (unsigned char c : value) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[7];
                    sprintf_s(buf, "\\u%04x", c);
                    out += buf;
                } else {
                    out += static_cast<char>(c);
                }
        }
    }
    return out;
}

static bool WriteTextFile(const std::string& path, const std::string& text) {
    if (path.empty()) return false;
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    if (!f.is_open()) return false;
    f << text;
    return true;
}

static std::string ReadTextFile(const std::string& path) {
    if (path.empty()) return {};
    std::ifstream f(path, std::ios::binary);
    if (!f.is_open()) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static void LogBridge(const std::wstring& message, int type = SYSLOG_INFO) {
    Interface* ip = GetCOREInterface();
    LogSys* log = ip ? ip->Log() : nullptr;
    if (log) {
        log->LogEntry(type, NO_DIALOG, _T("MCP Bridge"), message.c_str());
    }
}

static void SetNativePipeRunningFlag(bool running) {
    HandlerHelpers::RunMAXScript(std::string("global MCP_NativePipeRunning; MCP_NativePipeRunning = ") +
        (running ? "true" : "false"));
}

static std::string BuildInstanceJson(
    const std::string& instance_id,
    const std::string& pipe_name) {
    DWORD pid = GetCurrentProcessId();
    std::ostringstream ss;
    ss << "{\n"
       << "  \"instance_id\": \"" << JsonEscape(instance_id) << "\",\n"
       << "  \"pid\": " << pid << ",\n"
       << "  \"pipe\": \"" << JsonEscape(pipe_name) << "\",\n"
       << "  \"max_version\": " << MAX_SDK_VERSION << "\n"
       << "}\n";
    return ss.str();
}

void ShowChat() {
    if (!g_gupInstance) return;

    extern void ProcessChatMessage(const std::string& text, MCPBridgeGUP* gup);
    extern void ProcessChatAction(const std::string& action, const std::string& detail, MCPBridgeGUP* gup);

    MCPChatUI::SetMessageCallback([](const std::string& text) {
        ProcessChatMessage(text, g_gupInstance);
    });
    MCPChatUI::SetActionCallback([](const std::string& action, const std::string& detail) {
        ProcessChatAction(action, detail, g_gupInstance);
    });

    MCPChatUI::Show(g_gupInstance);

    if (LLMClient::IsConfigured()) {
        MCPChatUI::AppendMessage("ai", "Chat ready. Model: " + LLMClient::GetConfig().model);
    } else {
        MCPChatUI::AppendMessage("system",
            "No API key. Edit %LOCALAPPDATA%\\3dsmax-mcp\\.env (add OPENROUTER_API_KEY), "
            "then /reload.");
    }
}

static void OnSystemStartupDone(void* param, NotifyInfo* info) {
    if (!g_gupInstance) return;
    UnRegisterNotification(OnSystemStartupDone, nullptr, NOTIFY_SYSTEM_STARTUP);

    // Register a global MAXScript struct with functions that call our C++ directly
    // via the hidden executor window's WM_USER message
    // The trick: we post WM_USER+0x4D43 with a special lParam to trigger ShowChat
    HandlerHelpers::RunMAXScript(
        "macroScript MCP_Chat category:\"MCP\" tooltip:\"Open MCP AI Chat\" buttonText:\"MCP Chat\" "
        "( on execute do ( "
        "  local hwnds = windows.getChildHWND 0 \"MCPBridgeExecutor\"; "
        "  if hwnds != undefined and hwnds.count > 0 do ( "
        "    windows.sendMessage hwnds[1] 0x5144 1 0 "
        "  ) "
        ") )"
    );
    HandlerHelpers::RunMAXScript(
        "macroScript MCP_Claim_This_Max category:\"MCP\" tooltip:\"Make this Max the active MCP target\" buttonText:\"MCP Claim This Max\" "
        "( on execute do ( "
        "  local hwnds = windows.getChildHWND 0 \"MCPBridgeExecutor\"; "
        "  if hwnds != undefined and hwnds.count > 0 do ( "
        "    windows.sendMessage hwnds[1] 0x5144 2 0 "
        "  ) "
        ") )"
    );
}

void MCPBridgeGUP::RegisterInstance() {
    EnsureRegistryDirs();
    WriteTextFile(InstancePath(instance_id_), BuildInstanceJson(instance_id_, pipe_name_utf8_));
}

void MCPBridgeGUP::UnregisterInstance() {
    std::string active = ReadTextFile(ActiveInstancePath());
    if (active.find("\"instance_id\": \"" + instance_id_ + "\"") != std::string::npos) {
        DeleteFileA(ActiveInstancePath().c_str());
    }
    DeleteFileA(InstancePath(instance_id_).c_str());
}

void MCPBridgeGUP::ClaimInstance() {
    RegisterInstance();
    if (WriteTextFile(ActiveInstancePath(), BuildInstanceJson(instance_id_, pipe_name_utf8_))) {
        LogBridge(L"MCP Bridge: this 3ds Max instance is now the active MCP target");
    } else {
        LogBridge(L"MCP Bridge: failed to write active instance file", SYSLOG_WARN);
    }
}

void MCPBridgeGUP::StartPipe() {
    if (pipe_server_ && pipe_server_->IsRunning()) {
        SetNativePipeRunningFlag(true);
        return;
    }

    pipe_server_ = std::make_unique<PipeServer>(this, HandlerHelpers::Utf8ToWide(pipe_name_utf8_));
    pipe_server_->Start();
    SetNativePipeRunningFlag(true);
    RegisterInstance();
    LogBridge(L"MCP Bridge: native pipe server started on " + HandlerHelpers::Utf8ToWide(pipe_name_utf8_));
}

void MCPBridgeGUP::StopPipe() {
    if (pipe_server_) {
        pipe_server_->Stop();
        pipe_server_.reset();
    }
    SetNativePipeRunningFlag(false);
}

bool MCPBridgeGUP::IsPipeRunning() const {
    return pipe_server_ && pipe_server_->IsRunning();
}

void ClaimNativeInstance() {
    if (g_gupInstance) g_gupInstance->ClaimInstance();
}

// ── GUP implementation ──────────────────────────────────────────
DWORD MCPBridgeGUP::Start() {
    g_gupInstance = this;
    executor_.Initialize();
    SetNativePipeRunningFlag(false);
    instance_id_ = "pid-" + std::to_string(GetCurrentProcessId());
    pipe_name_utf8_ = "\\\\.\\pipe\\3dsmax-mcp-" + instance_id_;

    // Chat UI init deferred out of DllMain — calling LoadLibraryW for
    // msftedit.dll under the loader lock deadlocks Max startup.
    MCPChatUI::Init(hInstance);

    StartPipe();

    // Init LLM client — reads %LOCALAPPDATA%\3dsmax-mcp\mcp_config.ini [llm]
    LLMClient::Init();

    if (LLMClient::IsConfigured()) {
        std::wstring model = HandlerHelpers::Utf8ToWide(LLMClient::GetConfig().model);
        LogBridge(L"MCP Bridge: Standalone chat ready (" + model + L")");
    }

    // Register macroscripts after Max is fully loaded
    RegisterNotification(OnSystemStartupDone, nullptr, NOTIFY_SYSTEM_STARTUP);

    return GUPRESULT_KEEP;
}

void MCPBridgeGUP::Stop() {
    // Drain detached chat threads (ProcessChatMessage launches std::thread.detach()
    // per user message; they sit in WinHTTP and capture `this`) before tearing
    // down the executor and chat UI, otherwise the thread resumes into freed
    // memory. Bounded so a stuck HTTP call doesn't hang Max shutdown forever.
    extern bool WaitForChatTurns(int timeout_ms);
    bool drained = WaitForChatTurns(5000);
    if (!drained) {
        Interface* ip = GetCOREInterface();
        LogSys* log = ip ? ip->Log() : nullptr;
        if (log) {
            log->LogEntry(SYSLOG_WARN, NO_DIALOG, _T("MCP Bridge"),
                _T("MCP Bridge: chat thread still in flight at shutdown — proceeding anyway"));
        }
    }

    MCPChatUI::Destroy();
    StopPipe();
    UnregisterInstance();
    executor_.Shutdown();
    g_gupInstance = nullptr;
}

void MCPBridgeGUP::DeleteThis() {
    delete this;
}
