import torch
from diffusers import AutoencoderKL
from transformer.microdit import LitMicroDiT, MicroDiT
import lightning as L
from lightning.pytorch.tuner import Tuner
from lightning.pytorch.callbacks import ModelCheckpoint
from config import BS, MODELS_DIR_BASE, EPOCHS, MASK_RATIO, VAE_CHANNELS, VAE_HF_NAME
from config import DIT_B as DIT
from dataset.preprocess_datasets import preprocess_datasets_main
from dataset.index_image_id_map import index_image_id_map_main

if __name__ == "__main__":
    preprocess_datasets_main(test=True)
    index_image_id_map_main()

    input_dim = VAE_CHANNELS  # 4 channels in latent space
    patch_size = (2, 2)
    embed_dim = DIT["embed_dim"]
    num_layers = DIT["num_layers"]
    num_heads = DIT["num_heads"]
    mlp_dim = embed_dim * 4
    caption_embed_dim = 1152  # SigLip embeds to 1152 dims
    # pos_embed_dim = 60
    pos_embed_dim = None
    # timestep_caption_embed_dim = 60
    timestep_caption_embed_dim = None
    num_experts = 8
    active_experts = 2
    patch_mixer_layers = 1
    dropout = 0.1
    embed_cat = False

    world_size = torch.cuda.device_count()

    vae = AutoencoderKL.from_pretrained(f"{VAE_HF_NAME}", cache_dir=f"{MODELS_DIR_BASE}/vae")
    model = MicroDiT(input_dim, patch_size, embed_dim, num_layers, 
                    num_heads, mlp_dim, caption_embed_dim, timestep_caption_embed_dim,
                    pos_embed_dim, num_experts, active_experts,
                    dropout, patch_mixer_layers, embed_cat)

    print("Number of parameters: ", sum(p.numel() for p in model.parameters()))

    print("Starting training...")

    model = LitMicroDiT(model, mask_ratio=MASK_RATIO, batch_size=BS, seed=0)

    checkpoint_callback = ModelCheckpoint(dirpath="models/diffusion/", every_n_epochs=1)

    trainer = L.Trainer(max_epochs=EPOCHS, callbacks=[checkpoint_callback])
    tuner = Tuner(trainer)
    tuner.lr_find(model)

    trainer.fit(model=model)

    print("Training complete.")
