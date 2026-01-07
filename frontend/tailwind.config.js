/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,jsx}"],
    theme: {
        extend: {
            colors: {
                brand: {
                    500: "#F05545",
                    600: "#d63c2d",
                    700: "#b9251a"
                }
            }
        }
    },
    plugins: []
};


