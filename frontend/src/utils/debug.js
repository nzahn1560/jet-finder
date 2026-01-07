// Debug utility to check environment variables
export function checkEnvVars() {
    const vars = {
        VITE_API_URL: import.meta.env.VITE_API_URL,
        VITE_SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL,
        VITE_SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY ? 'SET' : 'MISSING'
    };
    
    console.log('🔍 Environment Variables Check:', vars);
    
    // Check for missing critical vars
    const missing = [];
    if (!vars.VITE_API_URL) missing.push('VITE_API_URL');
    if (!vars.VITE_SUPABASE_URL) missing.push('VITE_SUPABASE_URL');
    if (vars.VITE_SUPABASE_ANON_KEY === 'MISSING') missing.push('VITE_SUPABASE_ANON_KEY');
    
    if (missing.length > 0) {
        console.error('❌ Missing environment variables:', missing);
        console.error('⚠️ Your site may not work correctly without these variables!');
    } else {
        console.log('✅ All environment variables are set');
    }
    
    return vars;
}

