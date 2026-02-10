// AudioWorklet processor for capturing raw PCM audio.
// Downsamples from browser sample rate to 16kHz and converts to Int16.
// Runs on a separate audio thread for low-latency processing.

class PCMProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._buffer = [];
        // Send chunks every ~100ms (1600 samples at 16kHz)
        this._chunkSize = 1600;
    }

    process(inputs) {
        var input = inputs[0];
        if (!input || !input[0]) return true;

        var channelData = input[0]; // mono channel
        // Downsample from sampleRate to 16000
        var ratio = sampleRate / 16000;

        for (var i = 0; i < channelData.length; i += ratio) {
            var idx = Math.floor(i);
            // Clamp to Int16 range
            var sample = Math.max(-1, Math.min(1, channelData[idx]));
            this._buffer.push(sample * 32767);
        }

        if (this._buffer.length >= this._chunkSize) {
            var chunk = new Int16Array(this._buffer.splice(0, this._chunkSize));
            this.port.postMessage({ pcmChunk: chunk }, [chunk.buffer]);
        }

        return true;
    }
}

registerProcessor("pcm-processor", PCMProcessor);
