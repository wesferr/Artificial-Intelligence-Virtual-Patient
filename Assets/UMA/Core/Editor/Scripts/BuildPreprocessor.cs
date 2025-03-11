﻿using UMA;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;

public class BuildPreprocessor : IPreprocessBuildWithReport
{
    public int callbackOrder  { get { return 0; } }

    public void OnPreprocessBuild(BuildReport report)
    {
        UMAAssetIndexer.Instance.UpdateReferences();
    }
}
