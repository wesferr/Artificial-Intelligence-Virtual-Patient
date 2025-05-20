using UnityEngine;
using System;
using System.IO;
using System.Net.WebSockets;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine.Audio;
using System.Collections.Generic;
using TMPro;

public class SocketManager : MonoBehaviour
{
    private string addoz = "ws://192.168.137.1:8765/oz";
    private string addai1 = "ws://192.168.137.1:8765/ai1";
    private string addai2 = "ws://192.168.137.1:8765/ai2";
    public GameObject canvas;
    private Task receiveOzTask;
    private Task receiveAi1Task;
    private Task receiveAi2Task;
    private bool receivingOz = false;
    private bool receivingAi1 = false;
    private bool receivingAi2 = false;
    private AudioRecorder audioRecorder;
    private ClientWebSocket webSocketOz;
    private ClientWebSocket webSocketAi1;
    private ClientWebSocket webSocketAi2;
    private AudioSource audioSource;

    public GameObject loiro;
    public GameObject moreno;

    private string casopaciente = "ai1";
    private int caso = 0;

    private Queue<AudioClip> audioQueue = new Queue<AudioClip>();
    private bool isPlayingAudio = false;

    void Start()
    {
        audioRecorder = gameObject.AddComponent<AudioRecorder>();
        webSocketOz = new ClientWebSocket();
        webSocketAi1 = new ClientWebSocket();
        webSocketAi2 = new ClientWebSocket();
        audioSource = loiro.GetComponent<AudioSource>();
        ConnectWebSocket();
    }

    async void ConnectWebSocketOZ()
    {
        try
        {
            if (webSocketOz.State == WebSocketState.None || webSocketOz.State == WebSocketState.Closed)
                await webSocketOz.ConnectAsync(new Uri(addoz), CancellationToken.None);
        }
        catch (Exception ex)
        {
        }
    }

    async void ConnectWebsocketAI1()
    {
        try
        {
            if (webSocketAi1.State == WebSocketState.None || webSocketAi1.State == WebSocketState.Closed)
                await webSocketAi1.ConnectAsync(new Uri(addai1), CancellationToken.None);
        }
        catch (Exception ex)
        {
        }
    }

    async void ConnectWebsocketAI2()
    {
        try
        {
            if (webSocketAi2.State == WebSocketState.None || webSocketAi2.State == WebSocketState.Closed)
                await webSocketAi2.ConnectAsync(new Uri(addai2), CancellationToken.None);
        }
        catch (Exception ex)
        {
        }
    }

    async void ConnectWebSocket()
    {
        ConnectWebSocketOZ();
        ConnectWebsocketAI1();
        ConnectWebsocketAI2();
        _ = ReceiveAudioData(); // Start receiving audio data asynchronously
    }

    void Update()
    {
        HandleInput();
        ReconnectIfNeeded();
        PlayNextAudio();
    }

    void HandleInput()
    {
        if (OVRInput.GetDown(OVRInput.RawButton.A))
        {
            // caso 0 é ai1
            if (caso == 0)
            {
                caso = 1;
                casopaciente = "oz";
                moreno.SetActive(true);
                loiro.SetActive(false);
                audioSource = moreno.GetComponent<AudioSource>();
                canvas.GetComponent<TextMeshProUGUI>().text = caso.ToString();
            }
            else if (caso == 1)
            {
                caso = 2;
                casopaciente = "oz";
                moreno.SetActive(false);
                loiro.SetActive(true);
                audioSource = loiro.GetComponent<AudioSource>();
                canvas.GetComponent<TextMeshProUGUI>().text = caso.ToString();
            }
            else if (caso == 2)
            {
                caso = 3;
                casopaciente = "ai2";
                moreno.SetActive(true);
                loiro.SetActive(false);
                audioSource = moreno.GetComponent<AudioSource>();
                canvas.GetComponent<TextMeshProUGUI>().text = caso.ToString();
            }
            else if (caso == 3)
            {
                caso = 0;
                casopaciente = "ai1";
                moreno.SetActive(false);
                loiro.SetActive(true);
                audioSource = loiro.GetComponent<AudioSource>();
                canvas.GetComponent<TextMeshProUGUI>().text = caso.ToString();
            }
        }
        if (OVRInput.GetDown(OVRInput.RawButton.X))
        {
            StartRecording(casopaciente);
        }
        if (OVRInput.GetUp(OVRInput.RawButton.X))
        {
            StopRecordingAndSend(casopaciente);
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

    async void ReconnectIfNeeded()
    {
        if (webSocketOz.State == WebSocketState.Closed)
        {
            Debug.LogWarning("WebSocket oz disconnected. Reconnecting...");
            ConnectWebSocketOZ();
        }

        if (webSocketAi1.State == WebSocketState.Closed)
        {
            Debug.LogWarning("WebSocket ai1 disconnected. Reconnecting...");
            ConnectWebsocketAI1();
        }

        if (webSocketAi2.State == WebSocketState.Closed)
        {
            Debug.LogWarning("WebSocket ai2 disconnected. Reconnecting...");
            ConnectWebsocketAI2();
        }
        _ = ReceiveAudioData(); // Start receiving audio data asynchronously
    }

    async void SendAudioFile(string filePath, string socketType)
    {
        try
        {
            byte[] audioData = File.ReadAllBytes(filePath);
            ClientWebSocket targetSocket = null;
            if (socketType == "oz")
            {
                targetSocket = webSocketOz;
            }
            else if (socketType == "ai1")
            {
                targetSocket = webSocketAi1;
            }
            else if (socketType == "ai2")
            {
                targetSocket = webSocketAi2;
            }
            // ClientWebSocket targetSocket = socketType == "oz" ? webSocketOz : webSocketAi;

            if (targetSocket.State == WebSocketState.Open)
            {
                await targetSocket.SendAsync(new ArraySegment<byte>(new byte[] {0}), WebSocketMessageType.Binary, true, CancellationToken.None);
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
        var buffer = new byte[1024 * 1024];

        if (!receivingOz && webSocketOz.State == WebSocketState.Open)
        {
            receivingOz = true;
            _ = ReceiveAudioDataFromSocket(webSocketOz, buffer, "oz").ContinueWith(_ => receivingOz = false);
        }
        if (!receivingAi1 && webSocketAi1.State == WebSocketState.Open)
        {
            receivingAi1 = true;
            _ = ReceiveAudioDataFromSocket(webSocketAi1, buffer, "ai1").ContinueWith(_ => receivingAi1 = false);
        }
        if (!receivingAi2 && webSocketAi2.State == WebSocketState.Open)
        {
            receivingAi2 = true;
            _ = ReceiveAudioDataFromSocket(webSocketAi2, buffer, "ai2").ContinueWith(_ => receivingAi2 = false);
        }
    }

    async Task ReceiveAudioDataFromSocket(ClientWebSocket webSocket, byte[] buffer, string socketType)
    {
        Debug.Log($"WebSocket State: {webSocket.State}");
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
        CloseWebSocket(webSocketAi1, "ai1");
        CloseWebSocket(webSocketAi2, "ai2");
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