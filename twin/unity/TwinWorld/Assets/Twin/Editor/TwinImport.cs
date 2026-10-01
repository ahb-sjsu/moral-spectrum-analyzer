using UnityEditor;

// Import rules for the twin's third-party assets (fetched by twin/unity/fetch_assets.py).
// Rocketbox avatars become humanoids so postures can be set through HumanPose and any humanoid
// motion retargets onto them. Normal maps of both sources are marked as normal maps.
public class TwinImport : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        var m = (ModelImporter)assetImporter;
        if (assetPath.Contains("/Rocketbox/"))
        {
            m.animationType = ModelImporterAnimationType.Human;
            m.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            m.importAnimation = false;
        }
        if (assetPath.Contains("/ThirdParty/"))
        {
            m.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            m.materialSearch = ModelImporterMaterialSearch.RecursiveUp;
            m.materialName = ModelImporterMaterialName.BasedOnMaterialName;
        }
    }

    void OnPreprocessTexture()
    {
        var t = (TextureImporter)assetImporter;
        string p = assetPath.ToLowerInvariant();
        if (p.Contains("/thirdparty/") && (p.Contains("_normal") || p.Contains("_nor_gl")))
            t.textureType = TextureImporterType.NormalMap;
    }
}
