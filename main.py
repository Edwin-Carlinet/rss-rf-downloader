import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import feedparser
import requests
from pydub import AudioSegment
import os
import threading
import sys
from pathlib import Path

class RSSDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RSS RF Downloader")
        self.root.geometry("800x700")
        self.feed_url = tk.StringVar()
        # Définir le chemin par défaut pour le dossier Musique selon l'OS
        if sys.platform.startswith("win"):
            default_music = str(Path.home() / "Music")
        else:
            default_music = str(Path.home() / "Musique")
        self.dest_path = tk.StringVar(value=default_music)
        self.entries = []
        self.selected_indices = []
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="URL du flux RSS:").pack(pady=5)
        tk.Entry(self.root, textvariable=self.feed_url, width=60).pack(pady=5)
        tk.Label(self.root, text="Chemin de destination:").pack(pady=5)
        path_frame = tk.Frame(self.root)
        path_frame.pack(pady=5)
        tk.Entry(path_frame, textvariable=self.dest_path, width=50).pack(side=tk.LEFT)
        tk.Button(path_frame, text="Parcourir", command=self.browse_folder).pack(side=tk.LEFT)
        tk.Button(self.root, text="Charger le flux", command=self.load_feed).pack(pady=5)
        self.titles_list = tk.Listbox(self.root, selectmode=tk.MULTIPLE, width=80, height=15)
        self.titles_list.pack(pady=10)
        tk.Button(self.root, text="Télécharger et convertir", command=self.start_download).pack(pady=20)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20, pady=10)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dest_path.set(folder)

    def load_feed(self):
        url = self.feed_url.get()
        if not url:
            messagebox.showerror("Erreur", "Veuillez saisir l'URL du flux RSS.")
            return
        self.titles_list.delete(0, tk.END)
        self.entries = []
        self.podcast_title = "Podcast"
        try:
            feed = feedparser.parse(url)
            # Correction d'accès au titre du podcast (FeedParserDict)
            podcast_title = getattr(feed.feed, 'title', None)
            if isinstance(podcast_title, str):
                self.podcast_title = podcast_title.strip().replace('/', '_').replace('\\', '_')
            for entry in feed.entries:
                self.entries.append(entry)
                entry_title = getattr(entry, 'title', None)
                if isinstance(entry_title, str):
                    self.titles_list.insert(tk.END, entry_title)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le flux: {e}")

    def start_download(self):
        self.selected_indices = self.titles_list.curselection()
        if not self.selected_indices:
            messagebox.showerror("Erreur", "Veuillez sélectionner au moins un titre.")
            return
        if not self.dest_path.get():
            messagebox.showerror("Erreur", "Veuillez choisir un chemin de destination.")
            return
        threading.Thread(target=self.download_selected, daemon=True).start()

    def download_selected(self):
        podcast_folder = os.path.join(self.dest_path.get(), str(self.podcast_title))
        os.makedirs(podcast_folder, exist_ok=True)
        total = len(self.selected_indices)
        for i, idx in enumerate(self.selected_indices):
            entry = self.entries[idx]
            audio_url = self.get_audio_url(entry)
            if audio_url:
                prefix = f"{i+1:03d}_"
                title = getattr(entry, 'title', f'track_{i+1}')
                self.download_and_convert(audio_url, title, prefix, podcast_folder)
            self.progress_var.set(((i+1)/total)*100)
            self.root.update_idletasks()
        messagebox.showinfo("Terminé", "Téléchargement et conversion terminés.")
        self.progress_var.set(0)

    def get_audio_url(self, entry):
        # Cherche le lien audio dans l'entrée RSS
        if 'enclosures' in entry:
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('audio'):
                    return enclosure.href
        if hasattr(entry, 'link'):
            return entry.link
        return None

    def download_and_convert(self, url, title, prefix, folder):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                safe_title = str(title).strip().replace('/', '_').replace('\\', '_')
                temp_path = os.path.join(folder, f"{prefix}{safe_title}.tmp")
                total_length = int(response.headers.get('content-length', 0))
                downloaded = 0
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_length > 0:
                                percent = (downloaded / total_length) * 100
                                self.progress_bar['value'] = percent
                                self.root.update_idletasks()
                audio = AudioSegment.from_file(temp_path)
                mp3_path = os.path.join(folder, f"{prefix}{safe_title}.mp3")
                if hasattr(audio, 'format') and audio.format and audio.format.lower() == "mp3":
                    os.rename(temp_path, mp3_path)
                else:
                    audio.export(mp3_path, format="mp3")
                    os.remove(temp_path)
        except Exception as e:
            print(f"Erreur pour {title}: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RSSDownloaderApp(root)
    root.mainloop()
