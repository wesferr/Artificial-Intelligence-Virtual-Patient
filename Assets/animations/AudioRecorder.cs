using UnityEngine;
using System.IO;

public class AudioRecorder : MonoBehaviour
{
    private AudioClip audioClip;
    private string filePath;
    private bool isRecording = false;

    public void StartRecording()
    {
        if (!isRecording)
        {
            audioClip = Microphone.Start(null, false, 10, 44100);
            isRecording = true;
        }
    }

    public void StopRecording()
    {
        if (isRecording)
        {
            Microphone.End(null);
            SaveWavFile();
            isRecording = false;
        }
    }

    private void SaveWavFile()
    {
        filePath = Path.Combine(Application.persistentDataPath, "record.wav");
        using (var fileStream = new FileStream(filePath, FileMode.Create))
        {
            byte[] wavFile = WavUtility.FromAudioClip(audioClip);
            fileStream.Write(wavFile, 0, wavFile.Length);
        }
    }

    public string GetFilePath()
    {
        return filePath;
    }
}