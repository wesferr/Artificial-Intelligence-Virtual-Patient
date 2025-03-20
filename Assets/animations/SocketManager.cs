using UnityEngine;
using System;
using System.IO;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine.Audio;
using System.Collections.Generic;

public class SocketManager : MonoBehaviour
{
    private AudioRecorder audioRecorder;
    private ClientWebSocket webSocketOz;
    private ClientWebSocket webSocketAi;
    public AudioSource audioSource;

    private Queue<AudioClip> audioQueue = new Queue<AudioClip>();
    private bool isPlayingAudio = false;

    void Start()
    {
        audioRecorder = gameObject.AddComponent<AudioRecorder>();
        webSocketOz = new ClientWebSocket();
        webSocketAi = new ClientWebSocket();
        ConnectWebSocket();
    }

    async void ConnectWebSocket()
    {
        try
        {
            Debug.Log("Connecting to WebSocket servers...");
            await webSocketOz.ConnectAsync(new Uri("ws://192.168.0.120:8765/oz"), CancellationToken.None);
            await webSocketAi.ConnectAsync(new Uri("ws://192.168.0.120:8765/ai"), CancellationToken.None);
            Debug.Log("WebSocket connections established.");
            _ = ReceiveAudioData(); // Start receiving audio data asynchronously
        }
        catch (Exception ex)
        {
            Debug.LogError($"WebSocket connection failed: {ex.Message}");
        }
    }

    void Update()
    {
        HandleInput();
        ReconnectIfNeeded();
        PlayNextAudio();
    }

    void HandleInput()
    {
        if (OVRInput.GetDown(OVRInput.RawButton.X))
        {
            StartRecording("ai");
        }
        if (OVRInput.GetUp(OVRInput.RawButton.X))
        {
            StopRecordingAndSend("ai");
        }
        if (OVRInput.GetDown(OVRInput.RawButton.A))
        {
            StartRecording("oz");
        }
        if (OVRInput.GetUp(OVRInput.RawButton.A))
        {
            StopRecordingAndSend("oz");
        }
    }

    void StartRecording(string socketType)
    {
        audioRecorder.StartRecording();
        Debug.Log($"Recording started for {socketType}.");
    }

    void StopRecordingAndSend(string socketType)
    {
        audioRecorder.StopRecording();
        Debug.Log($"Recording stopped for {socketType}.");
        SendAudioFile(audioRecorder.GetFilePath(), socketType);
    }

    void ReconnectIfNeeded()
    {
        if (webSocketAi.State == WebSocketState.Closed || webSocketOz.State == WebSocketState.Closed)
        {
            Debug.LogWarning("WebSocket disconnected. Reconnecting...");
            ConnectWebSocket();
        }
    }

    async void SendAudioFile(string filePath, string socketType)
    {
        try
        {
            byte[] audioData = File.ReadAllBytes(filePath);
            ClientWebSocket targetSocket = socketType == "oz" ? webSocketOz : webSocketAi;

            if (targetSocket.State == WebSocketState.Open)
            {
                await targetSocket.SendAsync(new ArraySegment<byte>(audioData), WebSocketMessageType.Binary, true, CancellationToken.None);
                Debug.Log($"Audio file sent to {socketType}.");
            }
            else
            {
                Debug.LogWarning($"WebSocket {socketType} is not open. Cannot send audio.");
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"Failed to send audio file to {socketType}: {ex.Message}");
        }
    }

    async Task ReceiveAudioData()
    {
        var buffer = new byte[1024 * 1024]; // 1MB buffer

        // Processamento de WebSockets em tarefas separadas
        var receiveOzTask = ReceiveAudioDataFromSocket(webSocketOz, buffer, "oz");
        var receiveAiTask = ReceiveAudioDataFromSocket(webSocketAi, buffer, "ai");

        await Task.WhenAll(receiveOzTask, receiveAiTask); // Aguarda ambas as tarefas
    }

    async Task ReceiveAudioDataFromSocket(ClientWebSocket webSocket, byte[] buffer, string socketType)
    {
        while (webSocket.State == WebSocketState.Open)
        {
            try
            {
                var result = await webSocket.ReceiveAsync(new ArraySegment<byte>(buffer), CancellationToken.None);
                if (result.MessageType == WebSocketMessageType.Binary)
                {
                    Debug.Log($"[{socketType}] Received audio data of size: {result.Count}");
                    AudioClip clip = ConvertToAudioClip(buffer, result.Count);
                    if (clip != null)
                    {
                        audioQueue.Enqueue(clip);
                    }
                }
                else
                {
                    Debug.LogWarning($"[{socketType}] Received non-binary message of type: {result.MessageType}");
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"[{socketType}] Error receiving audio data: {ex.Message}");
                break; // Sai do loop se ocorrer um erro
            }
        }
    }

    void PlayNextAudio()
    {
        if (isPlayingAudio || audioQueue.Count == 0)
            return;

        isPlayingAudio = true;
        AudioClip nextClip = audioQueue.Dequeue();
        audioSource.clip = nextClip;
        audioSource.Play();
        Debug.Log($"Playing audio clip of length: {nextClip.length}");

        StartCoroutine(WaitForAudioToFinish(nextClip.length));
    }

    System.Collections.IEnumerator WaitForAudioToFinish(float clipLength)
    {
        yield return new WaitForSeconds(clipLength);
        isPlayingAudio = false;
    }

    AudioClip ConvertToAudioClip(byte[] audioData, int dataSize)
    {
        try
        {
            float[] samples = new float[dataSize / 2];
            for (int i = 0; i < samples.Length; i++)
            {
                short sample = BitConverter.ToInt16(audioData, i * 2);
                samples[i] = sample / 32768.0f;
            }

            AudioClip clip = AudioClip.Create("ReceivedClip", samples.Length, 1, 24000, false);
            clip.SetData(samples, 0);
            return clip;
        }
        catch (Exception ex)
        {
            Debug.LogError($"Error converting audio data to AudioClip: {ex.Message}");
            return null;
        }
    }

    void OnApplicationQuit()
    {
        CloseWebSocket(webSocketOz, "oz");
        CloseWebSocket(webSocketAi, "ai");
    }

    async void CloseWebSocket(ClientWebSocket webSocket, string socketType)
    {
        if (webSocket.State == WebSocketState.Open)
        {
            try
            {
                await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Application ending", CancellationToken.None);
                Debug.Log($"WebSocket {socketType} closed.");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error closing WebSocket {socketType}: {ex.Message}");
            }
        }
    }
}