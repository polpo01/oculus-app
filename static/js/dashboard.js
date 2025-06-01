function connectCam() {
    const ip = document.getElementById("ipCam").value;
    const container = document.getElementById("videoContainer");
    container.innerHTML = `<img src="/video_feed?ip=${encodeURIComponent(ip)}" width="640">`;
}
