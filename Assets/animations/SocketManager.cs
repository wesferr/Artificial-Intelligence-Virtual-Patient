using UnityEngine;
using System;
using System.IO;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine.Networking;
using UnityEngine.Audio;

public class SocketManager : MonoBehaviour
{
    private AudioRecorder audioRecorder;
    private ClientWebSocket webSocket;
    public AudioSource audioSource;
    private AudioClip receivedClip;

    void Start()
    {
        audioRecorder = gameObject.AddComponent<AudioRecorder>();
        webSocket = new ClientWebSocket();
        ConnectWebSocket();
    }

    async void ConnectWebSocket()
    {
        await webSocket.ConnectAsync(new System.Uri("ws://localhost:8765/oz"), CancellationToken.None);
        ReceiveAudioData();
    }

    void Update()
    {
        if (OVRInput.GetDown(OVRInput.RawButton.X))
        {
            audioRecorder.StartRecording();
            Debug.LogWarning("Recording started");
        }

        if (OVRInput.GetUp(OVRInput.RawButton.X))
        {
            audioRecorder.StopRecording();
            Debug.LogWarning("Recording stopped");
            SendAudioFile(audioRecorder.GetFilePath());
        }
    }

    async void SendAudioFile(string filePath)
    {
        byte[] audioData = File.ReadAllBytes(filePath);
        await webSocket.SendAsync(new ArraySegment<byte>(audioData), WebSocketMessageType.Binary, true, CancellationToken.None);
    }

    async void ReceiveAudioData()
    {
        var buffer = new byte[1024 * 1024]; // 1MB buffer
        while (webSocket.State == WebSocketState.Open)
        {
            var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
            if (result.MessageType == WebSocketMessageType.Binary)
            {
                Debug.Log("Received audio data");
                PlayReceivedAudio(buffer, result.Count);
            }
        }
    }

    void PlayReceivedAudio(byte[] audioData, int dataSize)
    {
        float[] samples = new float[dataSize / 2];
        for (int i = 0; i < samples.Length; i++)
        {
            short sample = BitConverter.ToInt16(audioData, i * 2);
            samples[i] = sample / 32768.0f;
        }

        receivedClip = AudioClip.Create("ReceivedClip", samples.Length, 1, 44100, false);
        receivedClip.SetData(samples, 0);
        
        audioSource.clip = receivedClip;
        audioSource.Play();
    }

    void OnApplicationQuit()
    {
        webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Application ending", CancellationToken.None).Wait();
    }
}
