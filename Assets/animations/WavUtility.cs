using UnityEngine;
using System;
using System.IO;

public static class WavUtility
{
    const int HEADER_SIZE = 44;

    public static byte[] FromAudioClip(AudioClip audioClip)
    {
        var samples = new float[audioClip.samples];
        audioClip.GetData(samples, 0);

        byte[] wavFile = new byte[HEADER_SIZE + samples.Length * sizeof(short)];
        using (var memoryStream = new MemoryStream(wavFile))
        using (var writer = new BinaryWriter(memoryStream))
        {
            WriteHeader(writer, audioClip);
            WriteSamples(writer, samples);
        }

        return wavFile;
    }

    private static void WriteHeader(BinaryWriter writer, AudioClip audioClip)
    {
        int sampleRate = audioClip.frequency;
        int channels = audioClip.channels;
        int samples = audioClip.samples;

        writer.Write(new char[4] { 'R', 'I', 'F', 'F' });
        writer.Write(HEADER_SIZE + samples * sizeof(short) - 8);
        writer.Write(new char[4] { 'W', 'A', 'V', 'E' });
        writer.Write(new char[4] { 'f', 'm', 't', ' ' });
        writer.Write(16);
        writer.Write((short)1);
        writer.Write((short)channels);
        writer.Write(sampleRate);
        writer.Write(sampleRate * channels * sizeof(short));
        writer.Write((short)(channels * sizeof(short)));
        writer.Write((short)16);
        writer.Write(new char[4] { 'd', 'a', 't', 'a' });
        writer.Write(samples * sizeof(short));
    }

    private static void WriteSamples(BinaryWriter writer, float[] samples)
    {
        foreach (var sample in samples)
        {
            writer.Write((short)(sample * short.MaxValue));
        }
    }
}