/**
 * Componente Alpine.js de câmera — abre a câmera traseira diretamente,
 * sem permitir galeria. Suporta captura de foto e gravação de vídeo.
 *
 * Uso: <div x-data="camera()" ...>
 */
function camera() {
  return {
    // estado interno
    aberto: false,
    modo: 'foto',        // 'foto' | 'video'
    gravando: false,
    stream: null,
    mediaRecorder: null,
    chunks: [],
    midias: [],          // [{ blob, tipo, preview, nome }]
    erro: '',

    // ── Abrir câmera ──────────────────────────────────────────────────────────
    async abrirCamera(modo = 'foto') {
      this.erro = '';
      this.modo = modo;
      const constraints = {
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: modo === 'video',
      };
      try {
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        this.aberto = true;
        await this.$nextTick();
        const video = document.getElementById('camera-viewfinder');
        if (video) {
          video.srcObject = this.stream;
          await video.play();
        }
      } catch (e) {
        if (e.name === 'NotAllowedError') {
          this.erro = 'Permissão de câmera negada. Permita o acesso nas configurações do navegador.';
        } else if (e.name === 'NotFoundError') {
          this.erro = 'Câmera não encontrada neste dispositivo.';
        } else {
          this.erro = 'Erro ao acessar a câmera: ' + e.message;
        }
      }
    },

    fecharCamera() {
      this._pararStream();
      this.aberto = false;
      this.gravando = false;
      this.chunks = [];
    },

    _pararStream() {
      if (this.stream) {
        this.stream.getTracks().forEach(t => t.stop());
        this.stream = null;
      }
    },

    // ── Capturar foto ─────────────────────────────────────────────────────────
    tirarFoto() {
      const video = document.getElementById('camera-viewfinder');
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);

      canvas.toBlob(blob => {
        const nome = `foto_${Date.now()}.jpg`;
        this.midias.push({
          blob,
          tipo: 'foto',
          preview: URL.createObjectURL(blob),
          nome,
        });
        this.fecharCamera();
      }, 'image/jpeg', 0.92);
    },

    // ── Gravar vídeo ──────────────────────────────────────────────────────────
    iniciarGravacao() {
      this.chunks = [];
      const mimeType = MediaRecorder.isTypeSupported('video/mp4') ? 'video/mp4' : 'video/webm';
      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
      this.mediaRecorder.ondataavailable = e => { if (e.data.size > 0) this.chunks.push(e.data); };
      this.mediaRecorder.onstop = () => {
        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
        const nome = `video_${Date.now()}.${ext}`;
        const blob = new Blob(this.chunks, { type: mimeType });
        this.midias.push({
          blob,
          tipo: 'video',
          preview: URL.createObjectURL(blob),
          nome,
        });
        this.fecharCamera();
      };
      this.mediaRecorder.start();
      this.gravando = true;
    },

    pararGravacao() {
      if (this.mediaRecorder && this.gravando) {
        this.mediaRecorder.stop();
        this.gravando = false;
      }
    },

    removerMidia(idx) {
      URL.revokeObjectURL(this.midias[idx].preview);
      this.midias.splice(idx, 1);
    },

    // ── Upload para o servidor ────────────────────────────────────────────────
    async uploadMidias(entidadeTipo, entidadeId, setor = 'Geral') {
      const resultados = [];
      for (const m of this.midias) {
        const fd = new FormData();
        fd.append('arquivo', m.blob, m.nome);
        fd.append('entidade_tipo', entidadeTipo);
        fd.append('entidade_id', entidadeId);
        fd.append('setor', setor);
        const res = await fetch('/uploads/', { method: 'POST', body: fd });
        if (!res.ok) throw new Error('Falha no upload de ' + m.nome);
        resultados.push(await res.json());
      }
      this.midias = [];
      return resultados;
    },
  };
}
