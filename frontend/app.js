document.addEventListener("DOMContentLoaded", () => {
    if (window.lucide) lucide.createIcons();

    const message = document.getElementById("approvalMessage");

    document.getElementById("approveBtn").addEventListener("click", () => {
        message.textContent = "Approval recorded for demonstration. Production integration will resume the LangGraph checkpoint.";
        message.className = "text-xs text-emerald-400 mt-4";
    });

    document.getElementById("denyBtn").addEventListener("click", () => {
        message.textContent = "Remediation denied. The incident remains blocked and requires escalation.";
        message.className = "text-xs text-red-400 mt-4";
    });
});
