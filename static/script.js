document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const sendTopicBtn = document.getElementById('sendTopicBtn');
    const topicInput = document.getElementById('topicInput');
    const dialogueDiv = document.getElementById('dialogue');
    const audioPlayer = document.getElementById('audioPlayer');

    let intervalId;

    startBtn.addEventListener('click', () => {
        fetch('/signal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: 'start' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                intervalId = setInterval(fetchMessages, 2000);
            }
        });
    });

    stopBtn.addEventListener('click', () => {
        fetch('/signal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: 'stop' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                clearInterval(intervalId);
            }
        });
    });

    sendTopicBtn.addEventListener('click', () => {
        const topic = topicInput.value;
        fetch('/send-topic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ topic: topic })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                topicInput.value = '';
            }
        });
    });

    function fetchMessages() {
        fetch('/messages')
        .then(response => response.json())
        .then(data => {
            if (data.audioUrl && data.text && data.speaker) {
                const audioUrl = data.audioUrl;
                const text = data.text;
                const speaker = data.speaker;

                // Отображение текста диалога
                const messageDiv = document.createElement('div');
                messageDiv.innerHTML = `<strong>${speaker}:</strong> ${text}`;
                dialogueDiv.appendChild(messageDiv);

                // Воспроизведение звука
                audioPlayer.src = audioUrl;
                audioPlayer.play();
            }
        });
    }
});
