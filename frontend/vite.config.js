import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    base: "/", // Ensure assets are loaded from root
    server: {
        port: 5173,
        host: "0.0.0.0",
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: "dist",
        assetsDir: "assets",
        sourcemap: false,
        // Ensure proper asset paths
        rollupOptions: {
            output: {
                assetFileNames: "assets/[name].[hash].[ext]",
                chunkFileNames: "assets/[name].[hash].js",
                entryFileNames: "assets/[name].[hash].js"
            }
        }
    }
});


