using System;
using System.Collections;
using System.Collections.Generic;
using UMA;
using UnityEngine;

public class SRPAdjuster : MonoBehaviour
{
    [System.Serializable]
    public struct lightAdjustment
    {
        UMAUtils.PipelineType pipeline;
        public GameObject light;
        public float intensity;
        public Color color;
        public bool disabled;
    };

    public lightAdjustment[] HDRPAdjustments;
    public lightAdjustment[] URPAdjustments;

    // Start is called before the first frame update
    void Start()
    {
        StartCoroutine(UpdateAdjustments());
        DoUpdate();
    }

    private IEnumerator UpdateAdjustments()
    {
        yield return new WaitForSeconds(1);
        DoUpdate();
    }

    private void DoUpdate()
    {
        Debug.Log("Updating SRP Adjustments");
        UMAUtils.PipelineType pipeline = UMAUtils.DetectPipeline();
        lightAdjustment[] adjustments = null;

        if (pipeline == UMAUtils.PipelineType.HDPipeline)
        {
            Debug.Log("Using HDRP Adjustments");
            adjustments = HDRPAdjustments;
        }
        else if (pipeline == UMAUtils.PipelineType.UniversalPipeline)
        {
            Debug.Log("Using URP Adjustments");
            adjustments = URPAdjustments;
        }

        if (adjustments != null)
        {
            foreach (lightAdjustment adjustment in adjustments)
            {
                if (adjustment.disabled)
                {
                    adjustment.light.SetActive(false);
                }
                else
                {
                    adjustment.light.SetActive(true);
                    adjustment.light.GetComponent<Light>().intensity = adjustment.intensity;
                    adjustment.light.GetComponent<Light>().color = adjustment.color;
                }
            }
        }
        else
        {
            Debug.Log("No adjustments found for this pipeline");
        }
    }
}
