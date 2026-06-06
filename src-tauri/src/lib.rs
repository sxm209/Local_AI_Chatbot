#[tauri::command]
fn app_name() -> &'static str {
    "Local AI Chatbot"
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![app_name])
        .run(tauri::generate_context!())
        .expect("error while running Local AI Chatbot");
}
