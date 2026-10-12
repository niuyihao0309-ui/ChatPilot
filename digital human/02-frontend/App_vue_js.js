// ============================================================
// App.vue 的 <script setup> 需要新增的 JS 片段
// 用法：整块粘进 App.vue 的 <script setup> 里（建议放在
//       playTts 函数之后，约第 600 行附近），并做 2 处小改动（见下）。
// 详见 02-前端改动说明.md
// ============================================================

// ── 数字人（魔珐星云）状态 ────────────────────────────────────
let liteSDK = null
const digitalHumanReady = ref(false)      // 资源下载完、可说话
const digitalHumanConnecting = ref(false) // 正在连接/下载
const digitalHumanProgress = ref(0)       // 下载进度 0-100
const digitalHumanError = ref('')         // 连接/取凭证失败提示

// 连接 / 断开 二合一按钮
async function toggleDigitalHuman() {
  digitalHumanError.value = ''

  // 已连接 → 断开销毁
  if (digitalHumanReady.value || digitalHumanConnecting.value) {
    try { liteSDK?.destroy() } catch (e) { /* 忽略销毁异常 */ }
    liteSDK = null
    digitalHumanReady.value = false
    digitalHumanConnecting.value = false
    digitalHumanProgress.value = 0
    return
  }

  // 未连接 → 初始化
  digitalHumanConnecting.value = true
  digitalHumanProgress.value = 0
  try {
    // 1. 从后端拿凭证（密钥不硬编码进前端源码）
    const resp = await fetch('/api/digital-human/credentials')
    if (!resp.ok) throw new Error('获取凭证失败')
    const cred = await resp.json()
    if (!cred.app_id || !cred.app_secret) {
      throw new Error('后端未配置数字人凭证，请填 .env 的 DIGITAL_HUMAN_APP_ID / _SECRET')
    }

    // 2. 创建 SDK 实例
    liteSDK = new XmovAvatar({
      containerId: '#digital-human-sdk',   // 注意必须带 #
      appId: cred.app_id,
      appSecret: cred.app_secret,
      gatewayServer: cred.gateway_server,
      hardwareAcceleration: 'prefer-hardware',
      enableLogger: true,                  // 开发期开日志排查
      onMessage(m) {
        // 50001/50002 是在线/离线切换，正常；其余才告警
        if (m?.code && m.code !== 50001 && m.code !== 50002) {
          digitalHumanError.value = 'SDK 错误 code=' + m.code + ' ' + (m.message || '')
        }
      },
    })

    // 3. 初始化连接：下资源 + 建 WebSocket；进度到 100% 才能 speak
    liteSDK.init({
      initModel: 'normal',
      onDownloadProgress(p) {
        digitalHumanProgress.value = p
        if (p >= 100 && !digitalHumanReady.value) {
          digitalHumanReady.value = true
          digitalHumanConnecting.value = false
        }
      },
    })
  } catch (e) {
    console.error('[数字人]', e)
    digitalHumanError.value = e instanceof Error ? e.message : '连接失败'
    digitalHumanConnecting.value = false
  }
}

// 让数字人读一段文字（一段完整的话：is_start=true, is_end=true）
function digitalHumanSpeak(text) {
  if (liteSDK && digitalHumanReady.value && text) {
    // 之前一句以 is_end=true 结束过，官方建议先切一次待机再 speak，口型才对齐
    liteSDK.interactiveidle()
    liteSDK.speak(text, true, true)
  }
}

// ============================================================
// 需要做的 2 处「小改动」（不是新增，是改现有行）：
//
// 【改动 1】sendPayload 里 appendBotMessages 之后加联动朗读（约第 466 行）
//   原：
//     appendBotMessages(data.messages ?? [])
//   改成：
//     appendBotMessages(data.messages ?? [])
//     // 数字人连上了就把文字类 Bot 回复同步读出来（对象卡片不读）
//     for (const m of (data.messages ?? [])) {
//       if (m.text) digitalHumanSpeak(m.text)
//     }
//   说明：没连数字人时 digitalHumanSpeak 内部判空直接返回，无害。
//
// 【改动 2】onUnmounted 里加 destroy（约第 567 行）
//   原：
//     onUnmounted(() => {
//       if (bgCanvas.value?._cleanup) bgCanvas.value._cleanup()
//     })
//   改成：
//     onUnmounted(() => {
//       if (bgCanvas.value?._cleanup) bgCanvas.value._cleanup()
//       try { liteSDK?.destroy() } catch (e) { /* 忽略 */ }  // 防并发超限 10005
//       liteSDK = null
//     })
//   说明：页面卸载前断开连接，释放魔珐房间资源，避免触发并发限制。
