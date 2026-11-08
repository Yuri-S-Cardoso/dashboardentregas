"""Endereços permitidos: loopback e IPv4 RFC1918, sem curingas."""
import ipaddress
import re
import socket

REDES_PRIVADAS = tuple(ipaddress.ip_network(r) for r in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
INTERFACES_EXCLUIDAS = re.compile(r"vpn|virtual|hyper-v|tap|\btun\b|wireguard|docker|wsl|vethernet|vmware|virtualbox|loopback", re.I)


def ipv4_privado(endereco):
    try:
        ip = ipaddress.ip_address(endereco)
        return isinstance(ip, ipaddress.IPv4Address) and any(ip in rede for rede in REDES_PRIVADAS)
    except ValueError:
        return False


def hosts_permitidos(texto):
    hosts = list(dict.fromkeys(h.strip() for h in texto.split(",") if h.strip()))
    if not hosts or any(h not in ("localhost", "127.0.0.1", "[::1]") and not ipv4_privado(h) for h in hosts):
        raise ValueError("ALLOWED_HOSTS aceita apenas localhost, loopback e IPv4 privado explícito; curingas e endereços públicos são proibidos.")
    return hosts


def interfaces_elegiveis(interfaces):
    """Um IPv4 por interface física Ethernet (6) ou Wi-Fi (71), ativa e Private."""
    elegiveis = {}
    # Prefere o IPv4 utilizável como origem. IPs adicionais não viram interfaces.
    for interface in sorted(interfaces, key=lambda i: (bool(i.get("secundario")), i.get("ip", ""))):
        if (ipv4_privado(interface.get("ip", ""))
                and interface.get("fisica") is True
                and interface.get("ativa") is True
                and interface.get("tipo") in (6, 71)
                and interface.get("perfil") == "Private"
                and isinstance(interface.get("indice"), int) and interface["indice"] > 0
                and not INTERFACES_EXCLUIDAS.search(interface.get("nome", "") + " " + interface.get("descricao", ""))):
            elegiveis.setdefault(interface["indice"], interface)
    return list(elegiveis.values())


def verificar_porta(enderecos, porta):
    if not 1 <= porta <= 65535:
        raise ValueError("A porta deve estar entre 1 e 65535.")
    for endereco in enderecos:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as teste:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                teste.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                teste.bind((endereco, porta))
            except OSError as erro:
                raise ValueError(f"Não foi possível usar {endereco}:{porta}. A porta pode estar ocupada ou o endereço não está disponível.") from erro
