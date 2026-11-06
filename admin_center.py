"""Cloud Admin Center: standalone GUI, cloud functions require separately deployed Worker."""
import json
import threading
import uuid
import customtkinter as ctk
from tkinter import messagebox
from cloud_license import request_json,normalize_server

ctk.set_appearance_mode('dark')
class AdminCenter(ctk.CTk):
 def __init__(self):
    super().__init__();self.title('YOUTUBE VIDEO DOWNLOADER — ADMIN CENTER');self.geometry('980x830')
    self.configure(fg_color='#090E1B')
    self.server=ctk.StringVar();self.secret=ctk.StringVar();self.owner=ctk.StringVar(value='Klient')
    self.duration=ctk.StringVar(value='30 dni');self.license_id=ctk.StringVar();self.extra=ctk.StringVar(value='30')
    ctk.CTkLabel(self,text='ADMIN CENTER 5.0 • PREMIUM CLOUD',font=('Segoe UI',23,'bold')).pack(pady=18)
    for label,var,show in [('Adres Worker HTTPS',self.server,None),('Sekret ADMIN_TOKEN (nie zapisujemy)',self.secret,'*'),('Odbiorca nowego kodu',self.owner,None)]:
      ctk.CTkLabel(self,text=label).pack(anchor='w',padx=25)
      ctk.CTkEntry(self,textvariable=var,show=show or '').pack(fill='x',padx=25,pady=3)
    ctk.CTkOptionMenu(self,variable=self.duration,values=['1 dzień','7 dni','30 dni','90 dni','365 dni','Bezterminowo','Własne dni']).pack(padx=25,anchor='w',pady=8)
    ctk.CTkLabel(self,text='Własna liczba dni / przedłużenie (dni)').pack(anchor='w',padx=25)
    ctk.CTkEntry(self,textvariable=self.extra).pack(fill='x',padx=25)
    controls=ctk.CTkFrame(self,fg_color='transparent');controls.pack(pady=12)
    for title,path in [('Generuj kod','/admin/issue'),('Lista licencji','/admin/list'),('Statystyki','/admin/stats'),('Unieważnij','/admin/revoke'),('Przedłuż','/admin/extend')]:
       ctk.CTkButton(controls,text=title,command=lambda p=path:self.execute(p),width=135).pack(side='left',padx=4)
    ctk.CTkLabel(self,text='ID licencji do unieważnienia lub przedłużenia').pack(anchor='w',padx=25)
    ctk.CTkEntry(self,textvariable=self.license_id).pack(fill='x',padx=25,pady=4)
    # Tokeny administratora: ID publiczne portfela, bez znajomości jego sekretnego klucza.
    token_panel=ctk.CTkFrame(self,fg_color='#182133',corner_radius=12)
    token_panel.pack(fill='x',padx=25,pady=12)
    ctk.CTkLabel(token_panel,text='TOKEN SHOP • ADMINISTRATOR',font=('Segoe UI',17,'bold')).pack(anchor='w',padx=15,pady=(10,4))
    self.wallet_id=ctk.StringVar()
    self.token_amount=ctk.StringVar(value='100')
    self.token_reason=ctk.StringVar(value='Nagroda administratora')
    for text,var in [('ID portfela użytkownika (UUID)',self.wallet_id),('Liczba tokenów (1–10000)',self.token_amount),('Powód przyznania',self.token_reason)]:
      row=ctk.CTkFrame(token_panel,fg_color='transparent');row.pack(fill='x',padx=15,pady=3)
      ctk.CTkLabel(row,text=text,width=265,anchor='w').pack(side='left')
      ctk.CTkEntry(row,textvariable=var).pack(side='left',fill='x',expand=True)
    buttons=ctk.CTkFrame(token_panel,fg_color='transparent');buttons.pack(pady=10)
    ctk.CTkButton(buttons,text='Sprawdź portfel',width=155,command=lambda:self.execute('/admin/token-wallet')).pack(side='left',padx=5)
    ctk.CTkButton(buttons,text='DODAJ TOKENY',width=160,fg_color='#b62340',command=lambda:self.execute('/admin/token-grant')).pack(side='left',padx=5)
    ctk.CTkLabel(token_panel,text='Operacja zapisywana w D1 i historii administratora. Nie przekazuj ADMIN_TOKEN graczom.',text_color='#9DACCA').pack(padx=15,pady=(0,10))
    self.output=ctk.CTkTextbox(self);self.output.pack(fill='both',expand=True,padx=25,pady=15)
    ctk.CTkLabel(self,text='Uwaga: kod aktywacyjny jest wyświetlany tylko w chwili tworzenia. Zachowaj go bezpiecznie.',text_color='#9DACCA').pack(pady=8)
 def execute(self,path):
    try:
      server=normalize_server(self.server.get());secret=self.secret.get().strip()
      if not secret:raise ValueError('Podaj sekret administratora')
      duration=self.duration.get();mapping={'1 dzień':1,'7 dni':7,'30 dni':30,'90 dni':90,'365 dni':365}
      minutes=None if duration=='Bezterminowo' else 1440*(mapping.get(duration) or int(self.extra.get()))
      if path in ('/admin/token-wallet','/admin/token-grant'):
        wallet_id=self.wallet_id.get().strip()
        if not wallet_id:raise ValueError('Wklej ID portfela użytkownika')
        if path=='/admin/token-wallet':args={'wallet_id':wallet_id}
        else:
          amount=int(self.token_amount.get().strip())
          reason=self.token_reason.get().strip()
          if not 1<=amount<=10000:raise ValueError('Dozwolone jest 1–10000 tokenów')
          if not reason or len(reason)>180:raise ValueError('Podaj powód (maks. 180 znaków)')
          if not messagebox.askyesno('Potwierdź przyznanie',f'Przyznać {amount} tokenów portfelowi\n{wallet_id}\nPowód: {reason}?'):
            return
          args={'wallet_id':wallet_id,'amount':amount,'reason':reason,'request_id':str(uuid.uuid4())}
      else:
        args={'/admin/issue':{'owner':self.owner.get(),'minutes':minutes},'/admin/list':{},'/admin/stats':{},'/admin/revoke':{'id':self.license_id.get().strip()},'/admin/extend':{'id':self.license_id.get().strip(),'minutes':int(self.extra.get())*1440}}[path]
    except (ValueError,KeyError) as exc:
      messagebox.showerror('Admin Center',str(exc));return
    def work():
      try:r=request_json(server,path,args,secret)
      except Exception as exc:r={'error':str(exc)[:250]}
      self.after(0,lambda:self.show(r))
    threading.Thread(target=work,daemon=True).start()
 def show(self,result):
    self.output.delete('1.0','end');self.output.insert('1.0',json.dumps(result,indent=2,ensure_ascii=False))

if __name__=='__main__':AdminCenter().mainloop()
