"""
Subjugate Online - Login Client
Handles login, registration, and character selection UI
"""

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import (
    DirectFrame, DirectButton, DirectEntry, DirectLabel,
    DirectScrolledFrame, DGG
)
from panda3d.core import TextNode, WindowProperties
import sys

from shared.constants import (
    LOGIN_SERVER_HOST, LOGIN_SERVER_PORT, PacketType, GameMode
)
from shared.utils import Logger
from server.network.protocol import Packet
from client.network_client import NetworkClient
from client.game_client import SubjugateOnlineClient

logger = Logger.get_logger(__name__)


class LoginClient(ShowBase):
    """Login client with GUI"""

    def __init__(self):
        ShowBase.__init__(self)

        # Network
        self.network = NetworkClient()
        self.setup_packet_handlers()

        # Session data
        self.session_token = None
        self.characters = []
        self.selected_character_id = None

        # UI state
        self.current_screen = None

        # Setup
        self.setup_window()
        self.show_login_screen()

        # Add network task
        self.taskMgr.add(self.network_task, "network")

        logger.info("Login client initialized")

    def setup_window(self):
        """Setup window"""
        props = WindowProperties()
        props.setTitle("Subjugate Online - Login")
        props.setSize(800, 600)
        self.win.requestProperties(props)

        # Set background color
        self.setBackgroundColor(0.1, 0.1, 0.15, 1)

    def clear_screen(self):
        """Clear current screen"""
        if self.current_screen:
            self.current_screen.destroy()
            self.current_screen = None

    def show_login_screen(self):
        """Show login/register screen"""
        self.clear_screen()

        frame = DirectFrame(frameColor=(0.2, 0.2, 0.25, 1.0),
                           frameSize=(-0.5, 0.5, -0.6, 0.6),
                           pos=(0, 0, 0))

        # Title
        DirectLabel(text="SUBJUGATE ONLINE",
                   scale=0.1,
                   pos=(0, 0, 0.45),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0))

        DirectLabel(text="Hardcore Ironman MMORPG",
                   scale=0.05,
                   pos=(0, 0, 0.35),
                   parent=frame,
                   text_fg=(0.8, 0.8, 0.8, 1),
                   frameColor=(0, 0, 0, 0))

        # Username
        DirectLabel(text="Username:",
                   scale=0.05,
                   pos=(-0.35, 0, 0.15),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0),
                   text_align=TextNode.ALeft)

        self.username_entry = DirectEntry(
            scale=0.05,
            pos=(-0.35, 0, 0.05),
            width=14,
            parent=frame,
            initialText="",
            numLines=1,
            focus=1
        )

        # Password
        DirectLabel(text="Password:",
                   scale=0.05,
                   pos=(-0.35, 0, -0.1),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0),
                   text_align=TextNode.ALeft)

        self.password_entry = DirectEntry(
            scale=0.05,
            pos=(-0.35, 0, -0.2),
            width=14,
            parent=frame,
            initialText="",
            numLines=1,
            obscured=1
        )

        # Status message
        self.status_label = DirectLabel(
            text="",
            scale=0.04,
            pos=(0, 0, -0.35),
            parent=frame,
            text_fg=(1, 0.5, 0.5, 1),
            frameColor=(0, 0, 0, 0)
        )

        # Buttons
        DirectButton(text="Login",
                    scale=0.06,
                    pos=(-0.15, 0, -0.5),
                    parent=frame,
                    command=self.do_login)

        DirectButton(text="Register",
                    scale=0.06,
                    pos=(0.15, 0, -0.5),
                    parent=frame,
                    command=self.do_register)

        self.current_screen = frame

        # Connect to login server
        if not self.network.is_connected():
            self.status_label.setText("Connecting to server...")
            if self.network.connect(LOGIN_SERVER_HOST, LOGIN_SERVER_PORT):
                self.status_label.setText("Connected! Please login.")
            else:
                self.status_label.setText("Failed to connect to server!")

    def do_login(self):
        """Perform login"""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.status_label.setText("Please enter username and password")
            return

        packet = Packet(PacketType.LOGIN_REQUEST, {
            'username': username,
            'password': password
        })

        self.network.send_packet(packet)
        self.status_label.setText("Logging in...")

    def do_register(self):
        """Perform registration"""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            self.status_label.setText("Please enter username and password")
            return

        packet = Packet(PacketType.REGISTER_REQUEST, {
            'username': username,
            'password': password
        })

        self.network.send_packet(packet)
        self.status_label.setText("Registering...")

    def show_character_select_screen(self):
        """Show character selection screen"""
        self.clear_screen()

        frame = DirectFrame(frameColor=(0.2, 0.2, 0.25, 1.0),
                           frameSize=(-0.6, 0.6, -0.7, 0.7),
                           pos=(0, 0, 0))

        # Title
        DirectLabel(text="SELECT CHARACTER",
                   scale=0.08,
                   pos=(0, 0, 0.6),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0))

        # Character list
        y_pos = 0.4
        for char in self.characters:
            char_frame = DirectButton(
                frameSize=(-0.5, 0.5, -0.08, 0.08),
                pos=(0, 0, y_pos),
                parent=frame,
                command=self.select_character,
                extraArgs=[char['id']]
            )

            mode_text = "UIM" if char['game_mode'] == GameMode.ULTIMATE_IRONMAN else "HIM"
            text = f"{char['name']} - Lv.{char['level']} - {mode_text} - Reincarnation: {char['reincarnation_count']}"

            DirectLabel(text=text,
                       scale=0.04,
                       pos=(0, 0, 0),
                       parent=char_frame,
                       text_fg=(1, 1, 1, 1),
                       frameColor=(0, 0, 0, 0))

            y_pos -= 0.15

        # Create character button
        DirectButton(text="Create New Character",
                    scale=0.06,
                    pos=(0, 0, -0.55),
                    parent=frame,
                    command=self.show_character_create_screen)

        # Back button
        DirectButton(text="Logout",
                    scale=0.05,
                    pos=(0, 0, -0.65),
                    parent=frame,
                    command=self.show_login_screen)

        self.current_screen = frame

    def show_character_create_screen(self):
        """Show character creation screen"""
        self.clear_screen()

        frame = DirectFrame(frameColor=(0.2, 0.2, 0.25, 1.0),
                           frameSize=(-0.5, 0.5, -0.5, 0.5),
                           pos=(0, 0, 0))

        # Title
        DirectLabel(text="CREATE CHARACTER",
                   scale=0.08,
                   pos=(0, 0, 0.4),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0))

        # Character name
        DirectLabel(text="Character Name:",
                   scale=0.05,
                   pos=(-0.4, 0, 0.2),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0),
                   text_align=TextNode.ALeft)

        self.char_name_entry = DirectEntry(
            scale=0.05,
            pos=(-0.4, 0, 0.1),
            width=16,
            parent=frame,
            initialText="",
            numLines=1
        )

        # Game mode selection
        DirectLabel(text="Game Mode:",
                   scale=0.05,
                   pos=(-0.4, 0, -0.05),
                   parent=frame,
                   text_fg=(1, 1, 1, 1),
                   frameColor=(0, 0, 0, 0),
                   text_align=TextNode.ALeft)

        self.game_mode = [GameMode.HARDCORE_IRONMAN]

        DirectButton(text="Hardcore Ironman (Can use bank)",
                    scale=0.045,
                    pos=(0, 0, -0.15),
                    parent=frame,
                    command=self.set_game_mode,
                    extraArgs=[GameMode.HARDCORE_IRONMAN])

        DirectButton(text="Ultimate Ironman (NO bank)",
                    scale=0.045,
                    pos=(0, 0, -0.25),
                    parent=frame,
                    command=self.set_game_mode,
                    extraArgs=[GameMode.ULTIMATE_IRONMAN])

        # Status
        self.create_status_label = DirectLabel(
            text="",
            scale=0.04,
            pos=(0, 0, -0.35),
            parent=frame,
            text_fg=(1, 0.5, 0.5, 1),
            frameColor=(0, 0, 0, 0)
        )

        # Buttons
        DirectButton(text="Create",
                    scale=0.06,
                    pos=(-0.15, 0, -0.45),
                    parent=frame,
                    command=self.do_create_character)

        DirectButton(text="Back",
                    scale=0.06,
                    pos=(0.15, 0, -0.45),
                    parent=frame,
                    command=self.request_character_list)

        self.current_screen = frame

    def set_game_mode(self, mode):
        """Set game mode selection"""
        self.game_mode[0] = mode
        self.create_status_label.setText(
            f"Selected: {'Ultimate Ironman' if mode == GameMode.ULTIMATE_IRONMAN else 'Hardcore Ironman'}"
        )

    def do_create_character(self):
        """Create character"""
        char_name = self.char_name_entry.get()

        if not char_name:
            self.create_status_label.setText("Please enter character name")
            return

        packet = Packet(PacketType.CHARACTER_CREATE_REQUEST, {
            'session_token': self.session_token,
            'character_name': char_name,
            'game_mode': self.game_mode[0]
        })

        self.network.send_packet(packet)
        self.create_status_label.setText("Creating character...")

    def select_character(self, character_id):
        """Select and enter game with character"""
        packet = Packet(PacketType.CHARACTER_SELECT_REQUEST, {
            'session_token': self.session_token,
            'character_id': character_id
        })

        self.network.send_packet(packet)
        self.selected_character_id = character_id

    def request_character_list(self):
        """Request character list"""
        packet = Packet(PacketType.CHARACTER_LIST_REQUEST, {
            'session_token': self.session_token
        })

        self.network.send_packet(packet)

    def launch_game_client(self, character_data, game_server_host, game_server_port):
        """Launch game client"""
        logger.info(f"Launching game client for {character_data['name']}")

        # Close login client
        self.network.disconnect()
        self.destroy()

        # Start game client
        game_client = SubjugateOnlineClient(character_data, self.session_token)

        # Connect to game server
        if game_client.connect_to_game_server(game_server_host, game_server_port):
            logger.info("Connected to game server, starting game...")
            game_client.run()
        else:
            logger.error("Failed to connect to game server")
            sys.exit(1)

    def network_task(self, task):
        """Process network packets"""
        self.network.process_incoming_packets()
        return task.cont

    # ========================================================================
    # PACKET HANDLERS
    # ========================================================================

    def setup_packet_handlers(self):
        """Setup packet handlers"""
        self.network.register_handler(PacketType.LOGIN_RESPONSE, self.handle_login_response)
        self.network.register_handler(PacketType.REGISTER_RESPONSE, self.handle_register_response)
        self.network.register_handler(PacketType.CHARACTER_LIST_RESPONSE, self.handle_character_list_response)
        self.network.register_handler(PacketType.CHARACTER_CREATE_RESPONSE, self.handle_character_create_response)
        self.network.register_handler(PacketType.CHARACTER_SELECT_RESPONSE, self.handle_character_select_response)

    def handle_login_response(self, packet: Packet):
        """Handle login response"""
        success = packet.data.get('success', False)
        message = packet.data.get('message', '')

        if success:
            self.session_token = packet.data.get('session_token')
            logger.info("Login successful")

            # Request character list
            self.request_character_list()
        else:
            self.status_label.setText(f"Login failed: {message}")

    def handle_register_response(self, packet: Packet):
        """Handle register response"""
        success = packet.data.get('success', False)
        message = packet.data.get('message', '')

        if success:
            self.status_label.setText("Registration successful! Please login.")
        else:
            self.status_label.setText(f"Registration failed: {message}")

    def handle_character_list_response(self, packet: Packet):
        """Handle character list response"""
        self.characters = packet.data.get('characters', [])
        self.show_character_select_screen()

    def handle_character_create_response(self, packet: Packet):
        """Handle character create response"""
        success = packet.data.get('success', False)
        message = packet.data.get('message', '')

        if success:
            # Refresh character list
            self.request_character_list()
        else:
            self.create_status_label.setText(f"Failed: {message}")

    def handle_character_select_response(self, packet: Packet):
        """Handle character select response"""
        success = packet.data.get('success', False)

        if success:
            character_data = packet.data.get('character_data', {})
            game_server_host = packet.data.get('game_server_host', '')
            game_server_port = packet.data.get('game_server_port', 0)

            # Launch game client
            self.launch_game_client(character_data, game_server_host, game_server_port)
        else:
            message = packet.data.get('message', '')
            logger.error(f"Character select failed: {message}")


def main():
    """Main entry point"""
    client = LoginClient()
    client.run()


if __name__ == '__main__':
    main()
