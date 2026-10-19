import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    // 5273：避开 Vite 默认的 5173。本机 XM-contract-approve 项目的前端也用 5173，
    // 两个项目会互相抢端口，导致一键启动脚本误判"前端已在运行"而跳过。
    port: 5273,
    // 端口被占时直接报错退出，不自动漂移到 5274/5175，保证脚本能可靠判断。
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
      '/commerce': {
        target: 'http://127.0.0.1:18081',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/commerce/, ''),
      },
      '/health': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
    },
  },
})
