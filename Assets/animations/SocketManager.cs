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
    private ClientWebSocket webSocketOz;
    private ClientWebSocket webSocketAi;
    public AudioSource audioSource;
    private AudioClip receivedClip;

    void Start()
    {
        audioRecorder = gameObject.AddComponent<AudioRecorder>();
        webSocketOz = new ClientWebSocket();
        webSocketAi = new ClientWebSocket();
        ConnectWebSocket();
    }

    async void ConnectWebSocket()
    {
        await webSocketOz.ConnectAsync(new System.Uri("ws://192.168.0.120:8765/oz"), CancellationToken.None);
        await webSocketAi.ConnectAsync(new System.Uri("ws://192.168.0.120:8765/ai"), CancellationToken.None);
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
            SendAudioFile(audioRecorder.GetFilePath(), "ai");
        }
        if (OVRInput.GetDown(OVRInput.RawButton.A))
        {
            audioRecorder.StartRecording();
            Debug.LogWarning("Recording started");
        }

        if (OVRInput.GetUp(OVRInput.RawButton.A))
        {
            audioRecorder.StopRecording();
            Debug.LogWarning("Recording stopped");
            SendAudioFile(audioRecorder.GetFilePath(), "oz");
        }

        if(webSocketAi.State == WebSocketState.Closed && webSocketOz.State == WebSocketState.Closed)
        {
            ConnectWebSocket();
        }
    }

    async void SendAudioFile(string filePath, string socketType)
    {
        byte[] audioData = File.ReadAllBytes(filePath);
        if (socketType == "oz")
        {
            await webSocketOz.SendAsync(new ArraySegment<byte>(audioData), WebSocketMessageType.Binary, true, CancellationToken.None);
        }
        else if (socketType == "ai")
        {
            await webSocketAi.SendAsync(new ArraySegment<byte>(audioData), WebSocketMessageType.Binary, true, CancellationToken.None);
        }
    }

    async void ReceiveAudioData()
    {
        var buffer = new byte[1024 * 1024]; // 1MB buffer
        while (webSocketOz.State == WebSocketState.Open && webSocketAi.State == WebSocketState.Open)
        {
            if (webSocketOz.State == WebSocketState.Open)
            {
                await ReceiveAudioDataFromSocket(webSocketOz, buffer);
            }
            if (webSocketAi.State == WebSocketState.Open)
            {
                await ReceiveAudioDataFromSocket(webSocketAi, buffer);
            }
        }
    }

    async Task ReceiveAudioDataFromSocket(ClientWebSocket webSocket, byte[] buffer)
    {
        var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
        if (result.MessageType == WebSocketMessageType.Binary)
        {
            Debug.Log("Received audio data");
            PlayReceivedAudio(buffer, result.Count);
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

        receivedClip = AudioClip.Create("ReceivedClip", samples.Length, 1, 24000, false);
        receivedClip.SetData(samples, 0);
        
        audioSource.clip = receivedClip;
        audioSource.Play();
    }

    void OnApplicationQuit()
    {
        webSocketOz.CloseAsync(WebSocketCloseStatus.NormalClosure, "Application ending", CancellationToken.None).Wait();
        webSocketAi.CloseAsync(WebSocketCloseStatus.NormalClosure, "Application ending", CancellationToken.None).Wait();
    }
}
