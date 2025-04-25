document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const sendTopicBtn = document.getElementById('sendTopicBtn');
    const topicInput = document.getElementById('topicInput');
    const dialogueDiv = document.getElementById('dialogue');
    const audioPlayer = document.getElementById('audioPlayer');

    let intervalId;
    let isPlaying = false;
    let audioQueue = [];

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
        const topic = topicInput.value.trim();
        if (topic) {
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
            })
            .catch(error => {
                console.error('Error sending topic:', error);
            });
        }
    });

    function fetchMessages() {
        fetch('/messages')
        .then(response => response.json())
        .then(data => {
            if (data.audioUrl && data.text && data.speaker) {
                audioQueue.push({
                    audioUrl: data.audioUrl,
                    text: data.text,
                    speaker: data.speaker
                });
                playNextAudio();
            }
        })
        .catch(error => {
            console.error('Error fetching messages:', error);
        });
    }

    function playNextAudio() {
        if (isPlaying || audioQueue.length === 0) {
            return;
        }

        const nextAudio = audioQueue.shift();
        isPlaying = true;

        // Отображение текста диалога
        const messageDiv = document.createElement('div');
        messageDiv.innerHTML = `<strong>${nextAudio.speaker}:</strong> ${nextAudio.text}`;
        dialogueDiv.appendChild(messageDiv);

        // Воспроизведение звука
        audioPlayer.src = nextAudio.audioUrl;
        audioPlayer.play();

        audioPlayer.onended = () => {
            isPlaying = false;
            playNextAudio();
        };
    }
});
