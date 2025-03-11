#define USING_BAKEMESH
using System;
using System.Collections.Generic;
using UMA.CharacterSystem;
using Unity.Collections;
using UnityEngine;


namespace UMA
{
    [Serializable]
    public class UMAUVAttachedItem 
    {
        public Vector2 uVLocation;
        public Vector2 uvUp;
		// Debugging
		public Vector2 uvInAtlas;
		public Rect uvArea;

        public string slotName;
        public Quaternion rotation;
        public Vector3 normalAdjust;
        public Vector3 translation;
        public GameObject prefab;
        public string boneName;
        public string sourceSlotName;
        public bool useMostestBone;

        public GameObject prefabInstance;
        public int subMeshNumber;
        public List<int> triangle = new List<int>();
        public SkinnedMeshRenderer skin;
        private Mesh tempMesh;
        private UMAData umaData;
        private Transform mostestBone;
        public Vector3 originalPosition;
        public Vector3 normal;
        public Vector3 normalMult = Vector3.one;
		public List<UMAUVAttachedItemBlendshapeAdjuster> blendshapeAdjusters = new List<UMAUVAttachedItemBlendshapeAdjuster>();

        public bool InitialFound = false;
        public float DistanceFromBone = 0.0f;
        public float InitialDistanceFromBone = 0.0f;

        public enum PrefabStatus
        {
            ShouldBeActivated,
            ShouldBeDeactivated,
            ShouldBeDeleted
        }

        public PrefabStatus prefabStatus = PrefabStatus.ShouldBeActivated;

        private struct BonesAndWeights
        {
            public Transform Bone;
            public float Weight;
            public Vector3 Normal;
        }

        private struct UVVerts
        {
            public int positionVertex;
            public int upVertex;
            public Vector3 InitialPosition;
        }

        private List<BonesAndWeights> weights;

        public bool worldTransform;
        private UVVerts uvVerts;

        public void CleanUp()
        {
            if (prefabInstance != null)
            {
                GameObject.Destroy(prefabInstance);
                prefabInstance = null;
            }
        }

        public void Setup(UMAData umaData, UMAUVAttachedItemLauncher bootstrap, bool Activate)
        {
            if (tempMesh == null)
            {
                tempMesh = new Mesh();
                uvVerts = new UVVerts();
                subMeshNumber = -1;
                blendshapeAdjusters.Clear();
                for (int i = 0; i < bootstrap.blendshapeAdjusters.Count; i++) {
                    UMAUVAttachedItemBlendshapeAdjuster bsa = bootstrap.blendshapeAdjusters[i];
                    blendshapeAdjusters.Add(new UMAUVAttachedItemBlendshapeAdjuster(bsa));
				}

                normalAdjust = bootstrap.normalAdjust;
                uVLocation = bootstrap.uVLocation;
                uvUp = bootstrap.uVUp;
                slotName = bootstrap.slotName;
                rotation = bootstrap.rotation;
                translation = bootstrap.translation;
                prefab = bootstrap.prefab;
                boneName = bootstrap.boneName;
                sourceSlotName = bootstrap.sourceSlot.slotName;
                useMostestBone = bootstrap.useMostestBone;
                this.umaData = umaData;
            }
            this.prefabStatus = Activate ? PrefabStatus.ShouldBeActivated : PrefabStatus.ShouldBeDeactivated;
        }

        public void ProcessSlot(UMAData umaData, SlotData slotData, DynamicCharacterAvatar avatar)
        {
            if (slotData != null)
            {
                Debug.Log($"Processing slot {slotData.slotName}");
                Vector2 UVInAtlas = slotData.ConvertToAtlasUV(uVLocation);
                Vector2 UvUpInAtlas = slotData.ConvertToAtlasUV(uvUp);
                SkinnedMeshRenderer smr = umaData.GetRenderer(slotData.skinnedMeshRenderer);

                Mesh mesh = smr.sharedMesh;
                subMeshNumber = slotData.submeshIndex;
                var smd = mesh.GetSubMesh(subMeshNumber);
                int maxVert = slotData.asset.meshData.vertexCount + slotData.vertexOffset;

				using(var dataArray = Mesh.AcquireReadOnlyMeshData(mesh)) {

					// slotData.ConvertToAtlasUV(uVLocation);\
					this.uvInAtlas = UVInAtlas;
					this.uvArea = slotData.UVArea;

                    Mesh.MeshData dat = dataArray[0];
                    var allUVS = new NativeArray<Vector2>(mesh.vertexCount, Allocator.Temp);
                    var allNormals = new NativeArray<Vector3>(mesh.vertexCount, Allocator.Temp);
                    var allVerts = new NativeArray<Vector3>(mesh.vertexCount, Allocator.Temp);

                    dat.GetUVs(0, allUVS);
                    dat.GetNormals(allNormals);
                    dat.GetVertices(allVerts);
                    uvVerts = FindVert(slotData, maxVert, UVInAtlas, UvUpInAtlas, allUVS);
                    Debug.Log($"Found vertex {uvVerts.positionVertex}");
                    triangle = FindTriangle(uvVerts.positionVertex, dat, mesh);
                    mostestBone = GetMostestBone(uvVerts.positionVertex, mesh, smr);
                }
                prefabStatus = PrefabStatus.ShouldBeActivated;
            }
            else
            {
                // either should be deleted, or should be deactivated.
                Debug.Log($"Processing hidden slot {slotName}");
                uvVerts = new UVVerts();
                triangle.Clear();
                mostestBone = null;
            }

            // No prefab, and should be deleted. So we are done.
            if (prefabInstance == null && prefabStatus == PrefabStatus.ShouldBeDeleted)
            {
                return;
            }

            if (prefabInstance == null)
            {
                Debug.Log("Creating prefab");
                if (useMostestBone)
                {
                    prefabInstance = GameObject.Instantiate(prefab, mostestBone);
                }
                else
                {
                    prefabInstance = GameObject.Instantiate(prefab, umaData.gameObject.transform);
                }
            }
            switch(prefabStatus)
            {
                case PrefabStatus.ShouldBeActivated:
                    prefabInstance.SetActive(true);
                    break;
                case PrefabStatus.ShouldBeDeactivated:
                    prefabInstance.SetActive(false);
                    break;
                case PrefabStatus.ShouldBeDeleted:
                    CleanUp();
                    break;
            }
        }

        private List<int> FindTriangle(int vert, Mesh.MeshData dat, Mesh mesh)
        {
            var f = dat.indexFormat;


            for (int i = 0; i < dat.subMeshCount; i++)
            {
                var mt = mesh.GetTopology(i);

                if (mt != MeshTopology.Triangles)
                {
                    continue;
                }
                var submesh = dat.GetSubMesh(i);
                var count = submesh.indexCount;

                var subIndices = new NativeArray<int>(count,Allocator.Temp);
                dat.GetIndices(subIndices, i);
                for(int j = 0; j < count; j+= 3)
                {
                    if (subIndices[j] == vert || subIndices[j+1] == vert || subIndices[j+2] == vert)
                    {
                        var tri = new List<int>(3);
                        tri.Add(subIndices[j]);
                        tri.Add(subIndices[j + 1]);
                        tri.Add(subIndices[j + 2]);
                        return tri;
                    }
                }
            }
            return new List<int>();
        }

        private Transform GetMostestBone(int vertexNumber, Mesh mesh, SkinnedMeshRenderer smr)
        {
            var weights = new List<BonesAndWeights>();
            var meshweights = mesh.GetAllBoneWeights();
            var meshbpv = mesh.GetBonesPerVertex();

            int myOffset = 0;

            // find the beginning of the bone
            for (int i = 0; i < vertexNumber; i++)
            {
                myOffset += meshbpv[i];
            }
            Transform mostestBone = smr.bones[meshweights[myOffset].boneIndex];

            Debug.Log($"Vertex {vertexNumber} Offset = {myOffset} in BoneWeights Mostest Bone = {mostestBone.gameObject.name}");
            return mostestBone;
        }

        private List<BonesAndWeights> GetBoneWeights(int vertexNumber, Mesh mesh, SkinnedMeshRenderer smr)
        {
            var weights = new List<BonesAndWeights>();
            var meshweights = mesh.GetAllBoneWeights();
            var meshbpv = mesh.GetBonesPerVertex();

            int myOffset = 0;

            // find the beginning of the bone
            for (int i = 0; i < vertexNumber; i++)
            {
                myOffset += meshbpv[i];
            }

            Debug.Log($"Vertex {vertexNumber} Offset = {myOffset} in BoneWeights");
            for(int i=myOffset; i < myOffset + meshbpv[vertexNumber]; i++)
            {
                BonesAndWeights boneWeights = new BonesAndWeights();
                boneWeights.Bone = smr.bones[meshweights[i].boneIndex];
                boneWeights.Weight = meshweights[i].weight;
                weights.Add(boneWeights);
            }
            Debug.Log($"weights size = {weights.Count}");
            return weights;
        }

        private UVVerts FindVert(SlotData slotData, int maxVert, Vector2 UV, Vector2 UvUp, NativeArray<Vector2> allUVS)
        {
            UVVerts verts = new UVVerts();
            verts.positionVertex = slotData.vertexOffset;
            float shortestDistance =   Mathf.Abs((allUVS[slotData.vertexOffset] - UV).magnitude);
            float shortestUpDistance = Mathf.Abs((allUVS[slotData.vertexOffset] - UvUp).magnitude);

            for (int i = slotData.vertexOffset + 1; i < maxVert; i++)
            {
                float thisDist = Mathf.Abs((allUVS[i] - UV).magnitude);
                float upDist = Mathf.Abs((allUVS[i]-UvUp).magnitude);
                    Vector3 restPos = slotData.asset.meshData.vertices[i - slotData.vertexOffset];

				if(thisDist < shortestDistance) 
				{
                    verts.InitialPosition = new Vector3(restPos.x, restPos.z, restPos.y);
                    verts.positionVertex = i;
                    shortestDistance = thisDist;
                }
                if (upDist < shortestUpDistance)
                {
                    verts.upVertex = i;
                    shortestUpDistance = upDist;
                }
            }

            return verts;
        }

        public Vector3 GetOffset(Vector3 position, Vector3 initialposition, DynamicCharacterAvatar avatar)
        {
            Vector3 offset = position - initialposition;
            return offset;
        }

		private Vector3 LerpVector(Vector3 a, Vector3 b, float t) 
		{
			if (Mathf.Approximately(t, 0f))
            {
                return a;
            }

            if (Mathf.Approximately(t, 1f))
            {
                return b;
            }

            Vector3 result = new Vector3();
			result.x = Mathf.Lerp(a.x, b.x, t);
			result.y = Mathf.Lerp(a.y, b.y, t);
			result.z = Mathf.Lerp(a.z, b.z, t);
			return result;
		}

		private Vector3 LerpAngle(Vector3 a, Vector3 b, float t) 
		{
			if(Mathf.Approximately(t, 0f))
            {
                return a;
            }

            if (Mathf.Approximately(t, 1f))
            {
                return b;
            }

            Vector3 result = new Vector3();
			result.x = Mathf.LerpAngle(a.x, b.x, t);
			result.y = Mathf.LerpAngle(a.y, b.y, t);
			result.z = Mathf.LerpAngle(a.z, b.z, t);
			return result;
		}

        public void DoLateUpdate(SkinnedMeshRenderer skin, Transform transform, DynamicCharacterAvatar avatar)
        {
            if (avatar != null && prefabInstance != null && uvVerts.positionVertex >= 0 && subMeshNumber >= 0)
            {
                Vector3 VertexInLocalSpace;
                int VertexNumber = uvVerts.positionVertex;

                skin.BakeMesh(tempMesh);
                using (var dataArray = Mesh.AcquireReadOnlyMeshData(tempMesh))
                {
                    var data = dataArray[0];
                    var allVerts = new NativeArray<Vector3>(tempMesh.vertexCount, Allocator.Temp);
                    data.GetVertices(allVerts);
                    var allNormals = new NativeArray<Vector3>(tempMesh.vertexCount, Allocator.Temp);
                    data.GetNormals(allNormals);
                    VertexInLocalSpace = allVerts[VertexNumber];
                    normal = allNormals[VertexNumber];


                    if (useMostestBone)
                    {
						Vector3 newNormalAdjust = new Vector3(normalAdjust.x, normalAdjust.y, normalAdjust.z);
						Vector3 newTranslation = new Vector3(translation.x, translation.y, translation.z);
#if true

                        for (int i = 0; i < blendshapeAdjusters.Count; i++) 
						{
                            UMAUVAttachedItemBlendshapeAdjuster bsAdjust = blendshapeAdjusters[i];
                            if (string.IsNullOrEmpty(bsAdjust.RaceName) || bsAdjust.RaceName == avatar.activeRace.name) 
								{
								SkinnedMeshRenderer smr = avatar.umaData.GetRenderer(0);
								int bsIndex = smr.sharedMesh.GetBlendShapeIndex(bsAdjust.BlendshapeName);
								if(bsIndex >= 0) {
									float bsWeight = smr.GetBlendShapeWeight(bsIndex)/100.0f;
									newTranslation = LerpVector(translation, bsAdjust.newOffset, bsWeight);
									newNormalAdjust = LerpAngle(normalAdjust, bsAdjust.newOrientation, bsWeight);
								}
								else 
								{
									newTranslation = bsAdjust.newOffset;
									newNormalAdjust = bsAdjust.newOrientation;
								}
							}
						}
 
                        Vector3 VertexInWorldSpace = transform.TransformPoint(VertexInLocalSpace);
                        Vector3 VertexInBoneSpace  = mostestBone.transform.InverseTransformPoint(VertexInWorldSpace);

                        prefabInstance.transform.localPosition = newTranslation + VertexInBoneSpace;
                        prefabInstance.transform.localRotation = Quaternion.Euler(newNormalAdjust);
#else

                        Vector3 MostestLocalBonePosition  = transform.worldToLocalMatrix * mostestBone.position; 

                        Vector3 BoneVector = VertexInLocalSpace - MostestLocalBonePosition;

                        // if things get goofy with initial position, perhap try using the 
                        // raw distance from the MeshData?
                        if (!InitialFound)
                        {
                            InitialDistanceFromBone = (MostestLocalBonePosition - VertexInLocalSpace).magnitude;
                            InitialFound = true;
                        }

                        float currentDistanceToBone = (MostestLocalBonePosition - VertexInLocalSpace).magnitude;
                                                  // 5                   // 1
                        float newPositionDelta = currentDistanceToBone - InitialDistanceFromBone;
                        
                        if (newPositionDelta != 0.0f)
                        {
                            Vector3 MoveVector = BoneVector.normalized;
                            VertexInLocalSpace = MostestLocalBonePosition + (MoveVector * currentDistanceToBone);
                        }

                       
                        Vector3 init = uvVerts.InitialPosition;
                        prefabInstance.transform.localPosition = this.translation + VertexInLocalSpace; 
                       // prefabInstance.transform.localRotation = this.rotation;
                       // position = transform.TransformPoint(position);

//                        normal = transform.TransformDirection(normal).normalized;
                        // prefabInstance.transform.localPosition = position;
 //                       prefabInstance.transform.rotation = Quaternion.Euler(normal);
#endif
                    } 
                    else
                    {
                        if (triangle.Count > 0)
                        {
                            Transform t = prefabInstance.transform;
#if global
                            Vector3 v1 = t.TransformPoint(allVerts[triangle[0]]);
                            Vector3 v2 = t.TransformPoint(allVerts[triangle[1]]);
                            Vector3 v3 = t.TransformPoint(allVerts[triangle[2]]);
#else
                            Vector3 v1 = allVerts[triangle[0]];
                            Vector3 v2 = allVerts[triangle[1]];
                            Vector3 v3 = allVerts[triangle[2]];
                            Vector3 vUp = VertexInLocalSpace - allVerts[uvVerts.upVertex];
#endif
                            Plane plane = new Plane(v1, v2, v3);
                            Vector3 newNormal = plane.normal;
                            t.localPosition = VertexInLocalSpace;
                            t.localRotation = Quaternion.FromToRotation(vUp,newNormal);
                        }
                        else
                        {
                            Vector3 newNormal = Vector3.Normalize(mostestBone.position - VertexInLocalSpace);                         
                            prefabInstance.transform.localPosition = VertexInLocalSpace;
                            prefabInstance.transform.localRotation = Quaternion.LookRotation(newNormal);
                        }
                    }
                }
                return;
            }
        }
    }
}

