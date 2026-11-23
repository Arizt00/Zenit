package studio.zenit.team;

import com.intellij.openapi.Disposable;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowFactory;
import com.intellij.ui.content.Content;
import com.intellij.ui.content.ContentFactory;
import com.intellij.ui.jcef.JBCefApp;
import com.intellij.ui.jcef.JBCefBrowser;
import javax.swing.*;
import java.awt.*;
import java.net.URI;

/** The same Monaco/Yjs client is hosted inside the IDE; no disk polling. */
public final class TeamToolWindow implements ToolWindowFactory {
  @Override public void createToolWindowContent(Project project, ToolWindow toolWindow) {
    JPanel panel=new JPanel(new BorderLayout(12,12));
    panel.setBorder(BorderFactory.createEmptyBorder(12,12,12,12));
    if(!JBCefApp.isSupported()){
      panel.add(new JLabel("Esta distribución necesita un JetBrains Runtime con JCEF. Abre la invitación en el navegador como alternativa."));
      toolWindow.getContentManager().addContent(ContentFactory.getInstance().createContent(panel,"Equipo",false));return;
    }
    JBCefBrowser browser=new JBCefBrowser();
    JPanel header=new JPanel(new BorderLayout(10,0));
    JPasswordField invitation=new JPasswordField();invitation.setToolTipText("Invitación completa de Zénit");
    JButton open=new JButton("Abrir equipo");header.add(invitation,BorderLayout.CENTER);header.add(open,BorderLayout.EAST);
    panel.add(header,BorderLayout.NORTH);panel.add(browser.getComponent(),BorderLayout.CENTER);
    open.addActionListener(event->{
      try{
        String value=new String(invitation.getPassword()).trim();URI uri=URI.create(value);
        if(!("http".equals(uri.getScheme())||"https".equals(uri.getScheme()))||uri.getHost()==null||uri.getUserInfo()!=null||uri.getFragment()==null||uri.getFragment().length()<32)throw new IllegalArgumentException();
        browser.loadURL(value);invitation.setText("");
      }catch(IllegalArgumentException error){JOptionPane.showMessageDialog(panel,"Introduce la invitación completa del anfitrión.","Co-Code",JOptionPane.WARNING_MESSAGE);}
    });
    Content content=ContentFactory.getInstance().createContent(panel,"Equipo",false);
    content.setDisposer((Disposable)browser);
    toolWindow.getContentManager().addContent(content);
  }
}
