using UnityEngine;
using UMA;
using UMA.CharacterSystem;

public class UMAAnimationOverride : MonoBehaviour
{
    public RuntimeAnimatorController customAnimator; // Arraste seu Animator Controller aqui
    private DynamicCharacterAvatar avatar;

    void Start()
    {
        avatar = GetComponent<DynamicCharacterAvatar>();

        // Adiciona um evento para definir o Animator depois que o avatar for gerado
        avatar.CharacterCreated.AddListener(OnCharacterCreated);
    }

    void OnCharacterCreated(UMAData data)
    {
        Animator animator = data.animator;
        if (animator != null && customAnimator != null)
        {
            animator.runtimeAnimatorController = customAnimator;
        }
    }
}
