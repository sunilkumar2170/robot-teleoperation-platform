/**
 * Teleop-Sim main entry point.
 */
document.addEventListener("DOMContentLoaded", async () => {
    const statusElem = document.getElementById("system-status");
    try {
        const res = await fetch("/health");
        if (res.ok) {
            const data = await res.json();
            if (statusElem) {
                statusElem.textContent = `Online: ${data.service} v${data.version} (${data.environment})`;
            }
        }
    } catch (e) {
        if (statusElem) {
            statusElem.textContent = "Backend offline or unreachable";
        }
    }
});
